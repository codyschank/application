from flask import Flask, render_template, flash, request, Response, session
from werkzeug.datastructures import Headers
from flask_googlemaps import GoogleMaps, Map
from secrets import *

import googlemaps
import psycopg2
import pandas as pd
import json

app = Flask(__name__)

app.config.from_object(__name__)

dbname = AUTH["dbname"]
username = AUTH["user"]
password = AUTH["pass"]
endpoint = AUTH["endpoint"]
flask_secret = AUTH["flask_secret"]
googlemaps_key = AUTH["googlemaps_key"]
googlemaps_key2 = AUTH["googlemaps_key2"]

app.config["SECRET_KEY"] = flask_secret  # for flask
app.config["GOOGLEMAPS_KEY"] = googlemaps_key  # for tiles
gmaps = googlemaps.Client(key=googlemaps_key2)

# Initialize the extension
GoogleMaps(app)

# Connect to make queries using psycopg2
con = psycopg2.connect(host=endpoint, database=dbname, user=username, password=password)

def handle_search(user_lng, user_lat, search_option):

    if(search_option == "radius"):

        sql_query = """
        SELECT oa_lat, oa_lon, oa_street_, oa_number, oa_street FROM select_final_addresses
        WHERE ST_Distance(geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),2163)) <= 400;
        """ % (
            user_lng,
            user_lat,
        )
        unregistered_addresses = pd.read_sql_query(sql_query, con)

    elif(search_option == "precinct"):

        sql_query = """
        SELECT cntyvtd, ST_Distance(pts.geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),2163)) as distance
        FROM select_final_addresses pts
        ORDER BY distance LIMIT 1;
        """ % (
            user_lng,
            user_lat,
        )
        cntyvtd_pd = pd.read_sql_query(sql_query, con)
        cntyvtd = str(cntyvtd_pd.cntyvtd.values[0])

        sql_query = """
        SELECT oa_lat, oa_lon, oa_street_, oa_number, oa_street FROM select_final_addresses
        WHERE cntyvtd = \'%s\';
        """ % (
            cntyvtd
        )
        unregistered_addresses = pd.read_sql_query(sql_query, con)

    return(unregistered_addresses)

def handle_address(address, search_option):

    geocode_result = gmaps.geocode(address)

    if not geocode_result:
        return render_template("result-fail.html")

    user_lat = geocode_result[0]["geometry"]["location"]["lat"]
    user_lng = geocode_result[0]["geometry"]["location"]["lng"]

    unregistered_addresses = handle_search(user_lng,user_lat,search_option)

    n_unregistered = unregistered_addresses.shape[0]
    formatted_address = geocode_result[0]["formatted_address"]

    session["search_option"] = search_option
    session["search_address"] = formatted_address
    session["user_lng"] = user_lng
    session["user_lat"] = user_lat

    # get just the fields needed for next steps
    unregistered_addresses = unregistered_addresses[['oa_lat', 'oa_lon', 'oa_street_']]
    unregistered_addresses["icon"] = "http://maps.google.com/mapfiles/ms/icons/green-dot.png"

    user_markers = [tuple(x) for x in unregistered_addresses.values]

    geocoded_location_tuple = [
        user_lat,
        user_lng,
        formatted_address,
        "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
    ]
    user_markers = user_markers + [
        geocoded_location_tuple
    ]  # + user_markers_radius_unregistered

    return render_template(
        "result-success.html",
        user_lat=user_lat,
        user_lng=user_lng,
        user_markers=user_markers,
        formatted_address=formatted_address,
        n_unregistered=n_unregistered,
        search_option=search_option
    )

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        address = request.form["address"]
        search_option = request.form["search_option"]
        if address:
            return handle_address(address, search_option)
        else:
            return render_template("result-fail.html")

    return render_template(
        "base.html",
    )

@app.route("/download")
def download():

    search_option = session.get("search_option")
    search_address = session.get("search_address")
    user_lng = session.get("user_lng")
    user_lat = session.get("user_lat")

    unregistered_addresses = handle_search(user_lng,user_lat,search_option)
    unregistered_addresses = unregistered_addresses[['oa_number', 'oa_street']]
    unregistered_addresses.columns = ['street_number','street_name']
    unregistered_addresses = unregistered_addresses.sort_values(['street_name', 'street_number'])
    csv = unregistered_addresses.to_csv(index=False)

    filename = search_address + " " + search_option + ".csv"

    headers = Headers()
    headers.set('Content-Disposition', 'attachment', filename=filename)
    return Response(csv, mimetype="text/csv",headers=headers)

if __name__ == "__main__":
    app.run(debug=True)
