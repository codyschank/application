from flask import Flask, render_template, flash, request, Response, send_file
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

import googlemaps
import psycopg2
import pandas as pd
import flask

app = Flask(__name__)

# following https://github.com/rochacbruno/Flask-GoogleMaps/blob/master/README.md

app.config.from_object(__name__)
app.config['SECRET_KEY'] = ''
app.config['GOOGLEMAPS_KEY'] = ''
gmaps = googlemaps.Client(key='')

# Initialize the extension
GoogleMaps(app)

# Set your postgres username
dbname = 'map_the_vote'
username = 'codyschank' # change this to your username

engine = create_engine('postgres://%s@localhost/%s'%(username,dbname))
print(engine.url)

## create a database (if it doesn't exist)
if not database_exists(engine.url):
    create_database(engine.url)
print(database_exists(engine.url))

# Connect to make queries using psycopg2
con = None
con = psycopg2.connect(database = dbname, user = username)

class ReusableForm(Form):
    name = TextField('Address:', validators=[validators.required()])

@app.route("/", methods=['GET', 'POST'])
def hello():

    # this is where I can establish default values for variables I get in the form
    address = '6205 Bon Terra Dr, Austin, TX 78731, USA'

    form = ReusableForm(request.form)

    print(form.errors)
    if request.method == 'POST':

        address=request.form['name']

        if form.validate():
            # Save the comment here.
            flash('You entered ' + address)
        else:
            flash('All the form fields are required. ')

    geocode_result = gmaps.geocode(address)
    user_lat = geocode_result[0]['geometry']['location']['lat']
    user_lng = geocode_result[0]['geometry']['location']['lng']

    sql_query = """
    SELECT oa_lat, oa_lon, oa_street_address FROM final_addresses_not_joined
    WHERE ST_Distance(geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) <= 400;
    """ % (user_lng, user_lat)
    unregistered_addresses = pd.read_sql_query(sql_query,con)
    n_unregistered = unregistered_addresses.shape[0]

    sql_query = """
    SELECT hdb_labels, ST_Distance(pts.geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) as distance
    FROM final_addresses_not_joined_hdbscan pts
    WHERE pts.hdb_labels > 0
    ORDER BY distance LIMIT 1;
    """ % (user_lng, user_lat)
    hdb_label_pd = pd.read_sql_query(sql_query,con)
    hdb_label = str(hdb_label_pd.hdb_labels.values[0])

    sql_query = """
    SELECT oa_lat, oa_lon, oa_street_ FROM final_addresses_not_joined_hdbscan
    WHERE hdb_labels = \'%s\';
    """ % (hdb_label)
    cluster_addresses = pd.read_sql_query(sql_query,con)
    n_cluster = cluster_addresses.shape[0]

    sql_query = """
    SELECT DISTINCT(oa_street_address) FROM tx25_join_3081
    WHERE ST_Distance(geom, ST_Transform(ST_GeomFromText('POINT(%s %s)',4326),3081)) <= 400;
    """ % (user_lng, user_lat)
    registered_addresses = pd.read_sql_query(sql_query,con)
    n_registered = registered_addresses.shape[0]

    n_total = n_unregistered + n_registered

    flash('Your search matched ' + geocode_result[0]['formatted_address'])
    #flash('There are ' + str(n_unregistered) + ' unregistered houses within a 1/4 mile radius of this address ' +
    #' out of ' + str(n_total) + ' total houses')
    flash('There are ' + str(n_cluster) + ' unregistered houses in the nearest cluster of houses')

    cluster_addresses['icon'] = 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'

    user_markers = [tuple(x) for x in cluster_addresses.values]

    geocoded_location_tuple = [user_lat,user_lng,geocode_result[0]['formatted_address'],'http://maps.google.com/mapfiles/ms/icons/blue-dot.png']
    user_markers = user_markers + [geocoded_location_tuple]

    cluster_addresses.to_csv("test.csv")

    return render_template('example_map.html', form=form, user_lat=user_lat, user_lng=user_lng, user_markers=user_markers)

@app.route('/heat_map.html')
def show_map():
    return flask.send_file('/heat_map.html')

if __name__ == '__main__':
    app.run(debug=True)
