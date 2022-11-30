from datetime import datetime, timedelta
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient,generate_container_sas, ContainerSasPermissions
import hashlib
import json
import math
import pathlib

import os
import requests
import google.auth.transport.requests

from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
import ast
import uuid
import time
from flask_caching import Cache

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from oauthlib.oauth2 import WebApplicationClient
from pip._vendor import cachecontrol
from flask import Flask, render_template, abort, jsonify, render_template, request, redirect, url_for, send_from_directory, json, session
from geofence import upload_geofence, check_geofence, check_within_latlng_500
import geocoder
import json
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.config.update(SECRET_KEY=uuid.uuid4().hex)

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

cv_subscription_key = app.config['CV_KEY']
cv_endpoint = app.config['CV_ENDPOINT']

cv_features = ["categories","brands","adult","color","objects"]

cv_client = ComputerVisionClient(
    cv_endpoint, CognitiveServicesCredentials(cv_subscription_key))

goog_client_id = app.config['GOOGLE_CLIENT_ID']
goog_client_secret = app.config['GOOGLE_CLIENT_SECRET']
goog_discovery_url = app.config['GOOGLE_DISCOVERY_URL']





cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)


# flag if test db is partitioned on city/category
is_city_partitioned = True

USER_DB = {}


# tmp
# this is to set our environment to https because OAuth 2.0 only supports https environments
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# set the path to where the .json file you got Google console is
client_secrets_file = os.path.join(
    pathlib.Path(__file__).parent, "client_secret.json")


flow = Flow.from_client_secrets_file(  # Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email",
            "openid"],  # here we are specifing what do we get after the authorization
    # and the redirect URI is the point where the user will end up after the authorization
    redirect_uri="http://127.0.0.1:5000/callback"
)


# a function to check if the user is authorized or not
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:  # authorization required
            return abort(401)
        else:
            return function()

    return wrapper


@app.route("/login")  # the page where the user can login
def login():
    # asking the flow class for the authorization (login) url
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


# this is the page that will handle the callback process meaning process after the authorization
@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # state does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(
        session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=goog_client_id
    )

    # defing the results to show on the page
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")

    user_id = hashlib.md5(str(session["name"]).encode()).hexdigest()
    USER_DB[user_id] = {"name": session["name"]}
    session["CURR_USER"] = user_id

    # the final page where the authorized users will end up
    return redirect("/home")


@app.route("/logout")  # the logout page and function
def logout():
    session.clear()
    return redirect("/")


@app.route("/")  # the home page where the login button will be located
def f():
    return " <a href='/login'><button>Login</button></a>"


# the page where only the authorized users can go to
@app.route("/protected_area")
@login_is_required
def protected_area():
    # the logout button
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"


@app.route('/post')
@cache.cached()
def index():
    print('Request for index page received')
    client_ips = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(request.headers)
    print(client_ips)
    print(request.remote_addr)
    client_ips = client_ips.split(':')[0]
    if client_ips is None or client_ips == '127.0.0.1':
        print('is none')
        client_ips = geocoder.ip('me').ip
    # else:
    #     client_ips = client_ips[0]
    msg=session.get('msg')
    if msg is None:
        msg= '' 
    print(msg)
    session['msg'] = ''
    session['name'] = ''
    print("ip:", client_ips)
    coords = geocoder.ip(str(client_ips)).latlng
    session["lat"], session["lng"] = coords[0], coords[1]
    session["city"] = geocoder.ip("me").city
    print('session message reset')
    return render_template('index.html', msg=msg)

@app.route('/query')
def query():
   print('Request for query page received')
   return render_template('query.html')

@app.route('/home')
def home():

    client_ips = request.headers.get('X-Forwarded-For', request.remote_addr)
    client_ips = client_ips.split(':')[0]

    if client_ips is None or client_ips == '127.0.0.1':
        print('is none')
        client_ips = geocoder.ip('me').ip

    print('Request for home page received')
    coords = geocoder.ip(str(client_ips)).latlng
    session["lat"], session["lng"] = coords[0], coords[1]
    session["city"] = geocoder.ip(str(client_ips)).city
    recent = read_recent()  # strcture = id=recent, last = last one, recents = values
    print(recent)
    recents = recent['recents']
    recents = ast.literal_eval(recents)
    print(recents)
    print(recents[0])

    last = int(recent['last'])-1
    recents = recents[last:] + recents[:last]
    rendering = []
    location_string = 'Looking at items from: ' + str(session['city'])
    for i in recents:
        output = {}
        print('i', i)
        read = cos_container.read_item(str(i), partition_key=str(i))
        try:
            if read['city'] != session['city']:
                continue
            try:
                img = ast.literal_eval(read['blob_id'])[0]
                img = get_img_url_with_container_sas_token(img)
                output['img'] = img
            except:
                output['img'] = ''
            name = read['title']
            output['name'] = name
            desc = read['desc']
            output['desc'] = desc
            output['id'] = i
            rendering += [output]
        except:
            continue
            # print('img', img)

    return render_template('home.html', recent=rendering, location = location_string, 
        other_home = "All Recent Items", other_home_link = url_for('home_all'))

@app.route('/home/all')
def home_all():
   print('Request for home page received')
   recent = read_recent() # strcture = id=recent, last = last one, recents = values
   print(recent)
   recents = recent['recents']
   recents = ast.literal_eval(recents)
   print(recents)
   print(recents[0])

   last = int(recent['last'])-1
   recents = recents[last:] + recents[:last]
   rendering = []
   for i in recents:
        output = {}
        print('i', i)
        read = cos_container.read_item(str(i), partition_key=str(i))
        try:
            img = ast.literal_eval(read['blob_id'])[0]
            img = get_img_url_with_container_sas_token(img)
            output['img'] = img
        except:
            output['img'] = ''
        name = read['title']
        output['name'] = name
        desc = read['desc']
        output['desc'] = desc
        output['id'] = i
        rendering += [output]
        # print('img', img)

   return render_template('home.html', recent=rendering, other_home = "Local Items", other_home_link = url_for('home'))

# using generate_container_sas
def get_img_url_with_container_sas_token(blob_name):
    container_sas_token = generate_container_sas(
        account_name=blob_account,
        container_name=blob_container,
        account_key=blob_key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    blob_url_with_container_sas_token = f"https://{blob_account}.blob.core.windows.net/{blob_container}/{blob_name}?{container_sas_token}"
    return blob_url_with_container_sas_token


@app.route('/query_load', methods=['POST','GET'])
def query_load():
    print('query_load')
    if request.method == "POST":
        item = request.form.get('itm')
        read = cos_container.read_item(str(item), partition_key=str(item))
        files = ast.literal_eval(read['blob_id'])
        # for file in files:
        img1 = img2 = img3 = img4 = ''
        try: 
            img1 = get_img_url_with_container_sas_token(files[0])
            img2 = get_img_url_with_container_sas_token(files[1])
            img3 = get_img_url_with_container_sas_token(files[2])
            img4 = get_img_url_with_container_sas_token(files[3])
        except:
            pass


        return render_template("query_load.html", id=item,  img1=img1, img2 = img2, img3=img3, img4=img4)#, ButtonPressed=ButtonPressed)
    return render_template("query_load.html", id = 'error')#, ButtonPressed = ButtonPressed)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
global post_id
post_id = 0

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')
   comment = request.form.get('freeform') 
   session['name'] = name
   print(comment)
   if name and comment:
       print('Request for hello page received with name=%s' % name)
       global post_id
       res, udid, city = upload_geofence([session['lng'], session['lat']], session['city'])
       if res in [200, 202]:
        post = {
            "name" : name,
            "comment":comment,
            "city": city,
            "fence_udid" : udid
        }
        print("geofence succesfful")
        post_id = insert_container(post)

       return render_template('hello.html', name = name, comment = comment)
   else:
       print('Request for hello page received with no name or comment -- redirecting')
       return redirect(url_for('index'))

@app.route('/item/<item_id>')
def item(item_id):
    read = cos_container.read_item(str(item_id), partition_key=str(item_id))
    try:
        imgs = ast.literal_eval(read['blob_id'])
        url_img = []
        for img in imgs:
            url_img += [get_img_url_with_container_sas_token(img)]
    except:
        url_img = []
    desc = read['desc']
    name = read['title']
    try:
        tags = read.get('tags')
        if tags is not None:
            tags = ast.literal_eval(tags)
            tags = str(tags)
    except:
        tags= ''

    return render_template('item.html', itemname = name, desc = desc, pics_list = url_img, tags = tags)



def insert_container(post,picture_id=''):
    title = post["name"]
    desc = post["comment"]
    city = post["city"]
    udid = post["fence_udid"]

    id = hashlib.md5(str(title).encode()).hexdigest()
    id = 'item'+id
    cos_container.upsert_item({
        'id':'{0}'.format(id),
        'test1' : 'test2',
        'city' : city,
        "fence_udid": udid, 
        'title' : '{0}'.format(str(title)),
        'desc' : '{0}'.format(str(desc)),
        'blob_id': '{0}'.format(str(picture_id))
    })
    return id

def update_container_pic(item, picture_id=''):
    print(str(item))
    read = cos_container.read_item(str(item), partition_key=str(item))
    cos_container.upsert_item({
        'id':'{0}'.format(item),
        'test1' : 'test',
        'city' : read['city'],
        "fence_udid": read['fence_udid'], 
        'title' : '{0}'.format(read['title']),
        'desc' : '{0}'.format(read['desc']),
        'blob_id': '{0}'.format(str(picture_id))
    })
    return id

def update_container_tags(item,tags=''):
    # print(str(item))
    read = cos_container.read_item(str(item), partition_key=str(item))
    cos_container.upsert_item({
        'id':'{0}'.format(item),
        'test1' : 'test',
        'title' : '{0}'.format(read['title']),
        'desc' : '{0}'.format(read['desc']),
        'city' : read["city"],
        'fence_udid' : read['fence_udid'],
        'blob_id': '{0}'.format(read['blob_id']),
        'tags':'{0}'.format(str(tags))
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
    print(len(items))
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

    lat, lng = session.get("lat"), session.get("lng")
    city = session.get("city")
    
    category = request.args.get('category', type = str)


    candidate_posts =  []

    # if category == "":
    #     candidate_posts = get_posts_by_city(city)
    # else:
    #     candidate_posts = get_posts_by_city_and_category(city, category)

    candidate_posts = get_posts_by_city(city)

    res = {"nearby_posts" : []}

    for post in candidate_posts:
        post = dict(post)
        if check_geofence(lat, lng, post.get("fence_udid")) :
            res["nearby_posts"].append(post)
    # print(res)
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
    return id

def read_recent():
    return cos_container.read_item(('recent'), partition_key='recent')

def update_recent(new_item):
    try:
        read = read_recent()
        print('read')
        last = int(read['last']) + 1 % 9
        print('last')
        recents = read['recents']
        recents = ast.literal_eval(recents)
        print('recents', recents)

        print('list')
        if len(recents) == 9:
            recents[last] = new_item
        else:
            recents.append(new_item)
        cos_container.upsert_item({
        'id':'{0}'.format('recent'),
        'last' : '{0}'.format(last),
        'recents':'{0}'.format(recents) 
    })
        print('sucess')
    except:
        last = 0
        recents = [new_item]
        cos_container.upsert_item({
        'id':'{0}'.format('recent'),
        'last' : '{0}'.format(last),
        'recents':'{0}'.format(recents) 
    })
        print('failed123')

        



blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in blob_allowed_ext

@app.route('/upload',methods=['POST'])
def upload():
    global post_id
    print('post2')
    if request.method == 'POST':
        print('post1')
        img = request.files.getlist('files[]')
        if len(img) > 0:
            file_names = []
            tags = []
            print('hgello123')
            msg = 'Uploading'
            for file in img:
                metadata = {}
                print(file.filename)
                if file and allowed_file(file.filename):
                    id = hashlib.md5(str(file.filename).encode())
                    blob_id = id.hexdigest()+'.'+file.filename.rsplit('.', 1)[1]
                    blob_client = blob_service_client.get_blob_client(
                        container=blob_container, blob=blob_id)
                    filename = secure_filename(file.filename)
                    file.save(filename)
                    file_names.append(blob_id)
                    with open(filename, "rb") as data:
                        try:
                            blob_client.upload_blob(data, overwrite=True)
                            metadata['filename'] = file.filename
                            blob_client.set_blob_metadata({"filename":file.filename})
                            img_url = get_img_url_with_container_sas_token(blob_id)
                            # CV may need retry pattern
                            result = cv_client.tag_image(img_url)
                            i = 0
                            for tag in result.tags:
                                if i < 5:
                                    tags += [tag.name]
                                    metadata['tag{0}'.format(i)] = tag.name
                                else:
                                    break
                                i += 1
                        except:
                            print('failed')
                            pass
                    blob_client.set_blob_metadata(metadata)
                    blob_client.set_blob_tags(metadata)
                item_name = session.get('name')

                msg = item_name + " has been uploaded to the server!"
                os.remove(filename)
            print(tags)
            tags = {tag : tags.count(tag) for tag in tags}
            update_container_pic(post_id, file_names)
            update_container_tags(post_id, tags)
            update_recent(post_id)
            session["msg"] = msg

            return redirect(url_for('index'))
            # render_template("index.html", msg=msg)
        else:
            session["msg"] = 'No pics provided.'
            return redirect(url_for('index'))
            # render_template("index.html", msg='No pics provided.')
    else:
        session["msg"] ='Upload failed.'
        return redirect(url_for('index'))

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
