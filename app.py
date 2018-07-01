from flask import Flask, render_template, flash, request, Response, send_file
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from secrets import *

import googlemaps
import psycopg2
import pandas as pd


import pdb

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



def handle_address(address):
    geocode_result = gmaps.geocode(address)
    user_lat = geocode_result[0]["geometry"]["location"]["lat"]
    user_lng = geocode_result[0]["geometry"]["location"]["lng"]

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
    cluster_addresses = pd.read_sql_query(sql_query, con)
    n_cluster = cluster_addresses.shape[0]

    sql_query = """
    SELECT oa_lat, oa_lon, oa_street_ FROM final_addresses_not_joined_hdbscan
    WHERE ST_Distance(geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) <= 400;
    """ % (
        user_lng,
        user_lat,
    )
    radius_unregistered_addresses = pd.read_sql_query(sql_query, con)
    n_radius_unregistered = radius_unregistered_addresses.shape[0]

    formatted_address = geocode_result[0]["formatted_address"]

    cluster_addresses["icon"] = "http://maps.google.com/mapfiles/ms/icons/green-dot.png"
    radius_unregistered_addresses[
        "icon"
    ] = "http://labs.google.com/ridefinder/images/mm_20_gray.png"

    user_markers_cluster = [tuple(x) for x in cluster_addresses.values]
    user_markers_radius_unregistered = [
        tuple(x) for x in radius_unregistered_addresses.values
    ]

    geocoded_location_tuple = [
        user_lat,
        user_lng,
        formatted_address,
        "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
    ]
    user_markers = user_markers_cluster + [
        geocoded_location_tuple
    ]  # + user_markers_radius_unregistered

    print(user_lat)

    return render_template(
        "results.html",
        user_lat=user_lat,
        user_lng=user_lng,
        user_markers=user_markers,
        formatted_address=formatted_address,
        n_cluster=n_cluster,
        n_radius_unregistered=n_radius_unregistered,
    )


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        address = request.form["address"]
        print('doing a thing!!!!!!!')
        return handle_address(address)
    
    return render_template(
        "base.html",
    )

if __name__ == "__main__":
    app.run(debug=True)



