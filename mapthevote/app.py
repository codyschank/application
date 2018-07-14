from flask import Flask, render_template, flash, request, Response, session
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from io import StringIO
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

def handle_address(address, option):
    geocode_result = gmaps.geocode(address)

    if not geocode_result:
        return render_template("result-fail.html")

    user_lat = geocode_result[0]["geometry"]["location"]["lat"]
    user_lng = geocode_result[0]["geometry"]["location"]["lng"]

    if(option == "option1"):

        sql_query = """
        SELECT hdb_labels, ST_Distance(pts.geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) as distance
        FROM final_addresses_not_joined_hdbscan pts
        WHERE pts.hdb_labels > 0
        ORDER BY distance LIMIT 1;
        """ % (
            user_lng,
            user_lat,
        )
        hdb_label_pd = pd.read_sql_query(sql_query, con)
        hdb_label = str(hdb_label_pd.hdb_labels.values[0])

        sql_query = """
        SELECT oa_lat, oa_lon, oa_street_ FROM final_addresses_not_joined_hdbscan
        WHERE hdb_labels = \'%s\';
        """ % (
            hdb_label
        )
        unregistered_addresses = pd.read_sql_query(sql_query, con)
        n_unregistered = unregistered_addresses.shape[0]

    elif(option == "option2"):

        sql_query = """
        SELECT oa_lat, oa_lon, oa_street_ FROM final_addresses_not_joined_hdbscan
        WHERE ST_Distance(geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) <= 400;
        """ % (
            user_lng,
            user_lat,
        )
        unregistered_addresses = pd.read_sql_query(sql_query, con)
        n_unregistered = unregistered_addresses.shape[0]

    if(option == "option3"):

        sql_query = """
        SELECT cntyvtd, ST_Distance(pts.geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) as distance
        FROM final_addresses_not_joined_hdbscan pts
        ORDER BY distance LIMIT 1;
        """ % (
            user_lng,
            user_lat,
        )
        cntyvtd_pd = pd.read_sql_query(sql_query, con)
        cntyvtd = str(cntyvtd_pd.cntyvtd.values[0])

        sql_query = """
        SELECT oa_lat, oa_lon, oa_street_ FROM final_addresses_not_joined_hdbscan
        WHERE cntyvtd = \'%s\';
        """ % (
            cntyvtd
        )
        unregistered_addresses = pd.read_sql_query(sql_query, con)
        n_unregistered = unregistered_addresses.shape[0]

    # save this to the session so it can be accessed by download function if needed
    session["unregistered_addresses"] = unregistered_addresses.oa_street_.to_dict()

    formatted_address = geocode_result[0]["formatted_address"]

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
        unregistered_addresses=unregistered_addresses
    )

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        address = request.form["address"]
        exampleRadios = request.form["exampleRadios"]
        if address:
            return handle_address(address, exampleRadios)
        else:
            return render_template("result-fail.html")

    return render_template(
        "base.html",
    )

@app.route("/download")
def download():
    unregistered_addresses = pd.DataFrame.from_dict(session.get("unregistered_addresses"), orient='index')
    unregistered_addresses.columns = ['address']
    csv = unregistered_addresses.to_csv(index=False)
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=test.csv"})

if __name__ == "__main__":
    app.run(debug=True)
