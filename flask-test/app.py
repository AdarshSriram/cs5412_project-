from datetime import datetime
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
import hashlib
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, json
from geofence import upload_geofence, check_geofence
import geocoder
import json

app = Flask(__name__)

app.config.from_pyfile('config.py')
cos_account = app.config['ACCOUNT_NAME']   # Azure account name
cos_key = app.config['ACCOUNT_KEY']      # Azure Storage account access key  
cos_connect_str = app.config['CONNECTION_STRING']
cos_container = app.config['CONTAINER'] # Container name
cos_allowed_ext = app.config['ALLOWED_EXTENSIONS'] # List of accepted extensions
cos_max_length = app.config['MAX_CONTENT_LENGTH'] # Maximum size of the uploaded file
cos_uri = app.config['URI']

client = CosmosClient(cos_uri, credential = cos_key)

cos_DATABASE_NAME = 'SampleDB'
cos_database = client.get_database_client(cos_DATABASE_NAME)
cos_CONTAINER_NAME = 'SampleContainer'
cos_container = cos_database.get_container_client(cos_CONTAINER_NAME)


blob_account = app.config['BLOB_ACCOUNT_NAME']   # Azure account name
blob_key = app.config['BLOB_ACCOUNT_KEY']      # Azure Storage account access key
blob_connect_str = app.config['BLOB_CONNECTION_STRING']
blob_container = app.config['BLOB_CONTAINER']  # Container name
blob_allowed_ext = app.config['BLOB_ALLOWED_EXTENSIONS']  # List of accepted extensions
# Maximum size of the uploaded file
blob_max_length = app.config['BLOB_MAX_CONTENT_LENGTH']

@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
def hello():
    name = request.form.get('name')
    description = request.form.get('description') 
    category = request.form.get('category') 
    user_id = request.form.get('user_id')
    if name:
        res, udid, city = upload_geofence()
        if res not in [200, 202]:
           print("unable to create goefence")
           return redirect(url_for('index'))
        
        print("geofence successful")

        post_id = insert_container((name, description, city, udid, user_id, category))

        return render_template('hello.html', name = user_id, comment = description)
    else:
       print('Request for hello page received with empty text -- redirecting')
       return redirect(url_for('index'))




def insert_container(data):
    name, description, city, udid, user_id, category = data
    id = hashlib.md5(str(name + user_id).encode())
    cos_container.upsert_item({
        'id':'item{0}'.format(id.hexdigest()),
        'user_id' : str(user_id),
        "item_name" : name,
        "description" : description,
        "fence_udid" : str(udid),
        "city" : city,
        "media_id" : "",
        "category" : category
    })
    return id


def get_posts_by_seller_id(seller_id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.user_id=@id",
    parameters=[
        { "name":"@id", "value": seller_id }
    ],
        enable_cross_partition_query=True
    ))
    return items

def get_posts_by_city(city):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.city=@city",
    parameters=[
        { "name":"@city", "value": city }
    ],
        enable_cross_partition_query=True
    ))
    return items

def get_posts_by_city_and_category(city, category):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.city=@city AND r.category=@category",
    parameters=[
        { "name":"@city", "value": city },
        { "name":"@category", "value": category },
    ],
        enable_cross_partition_query=True
    ))
    return items


@app.route('/nearby-posts',methods=['GET'])
def get_nearby_posts():
    coords = geocoder.ip("me").latlng
    lat, lng = coords[0], coords[1]
    city = geocoder.ip("me").city
    
    category = request.args.get('category', type = str)


    candidate_posts =  []

    if category == "":
        candidate_posts = get_posts_by_city(city)
    else:
        candidate_posts = get_posts_by_city_and_category(city, category)

    res = {"nearby_posts" : []}

    for post in candidate_posts:
        post = dict(post)
        if check_geofence(lat, lng, post.get("fence_udid")) :
            res["nearby_posts"].append(post)
    print(res)
    return json.dumps(res)


def get_post_by_id(post_id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.id=@id",
    parameters=[
        { "name":"@id", "value": post_id }
    ],
        enable_cross_partition_query=True
    ))
    return items

blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in blob_allowed_ext

@app.route('/upload',methods=['POST'])
def upload():
    print('post2')
    if request.method == 'POST':
        print('post1')
        img = request.files['file']
        print('hgello123')
        if img and allowed_file(img.filename):
            print('h23 d d')
            filename = secure_filename(img.filename)
            img.save(filename)
            print('hello')
            blob_client = blob_service_client.get_blob_client(container = blob_container, blob = filename)
            with open(filename, "rb") as data:
                try:
                    blob_client.upload_blob(data, overwrite=True)
                    msg = "Upload Done ! "
                except:
                    pass
            os.remove(filename)
    return render_template("index.html", msg=msg)


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


if __name__ == '__main__':
   app.run()
