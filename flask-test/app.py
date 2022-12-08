import ast
from collections import defaultdict
import hashlib
import json
from geofence_v2 import *
import redis
import math
import random
#app.py
import os
import pathlib
import uuid
import nltk
import logging
from datetime import datetime, timedelta
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from websocket import create_connection
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
import geocoder
import google.auth.transport.requests
import requests
import google.auth.transport.requests
from flask_caching import Cache
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
import ast
import uuid
from azure.cognitiveservices.vision.computervision.models import (
    OperationStatusCodes, VisualFeatureTypes)
from azure.cosmos import CosmosClient
from azure.storage.blob import (BlobServiceClient, ContainerSasPermissions,
                                generate_container_sas)
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL, leaderip, followerip, AZURE_SERVICE_BUS_CONN_STR
from flask_caching import Cache
from geofence import check_within_latlng_500
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from msrest.authentication import CognitiveServicesCredentials
from oauthlib.oauth2 import WebApplicationClient
from pip._vendor import cachecontrol
from flask import (Flask, render_template, abort, jsonify, render_template, request, redirect, url_for, send_from_directory, json, session)
from geofence import check_within_latlng_500
import json
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from word_forms.word_forms import get_word_forms
from oauthlib.oauth2 import WebApplicationClient
from pip._vendor import cachecontrol
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from azure.servicebus.management import ServiceBusAdministrationClient
from flask_session import Session
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
import rediscnfg
import urllib.request
import json
import os
import ssl

# import reverse_geocode


app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=72)

# LOGGER
LOGGER = logging.getLogger(__name__)

app.config.from_pyfile('config.py')
cos_account = app.config['ACCOUNT_NAME']   # Azure account name
cos_key = app.config['ACCOUNT_KEY']      # Azure Storage account access key  
cos_connect_str = app.config['CONNECTION_STRING']
cos_container = app.config['CONTAINER'] # Container name
cos_allowed_ext = app.config['ALLOWED_EXTENSIONS'] # List of accepted extensions
cos_max_length = app.config['MAX_CONTENT_LENGTH'] # Maximum size of the uploaded file
cos_uri = app.config['URI']

app.config.update(SECRET_KEY=uuid.uuid4().hex)

client = CosmosClient(cos_uri, credential = cos_key)

cos_DATABASE_NAME = 'Data'
cos_database = client.get_database_client(cos_DATABASE_NAME)
cos_CONTAINER_NAME = 'PostData1'
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

text_subscription_key = app.config['TEXT_KEY']
text_endpoint = app.config['TEXT_ENDPOINT']

cv_features = ["categories","brands","adult","color","objects"]

cv_client = ComputerVisionClient(
    cv_endpoint, CognitiveServicesCredentials(cv_subscription_key))

text_analytics_client = TextAnalyticsClient(
    endpoint=text_endpoint, credential=AzureKeyCredential(text_subscription_key))

# myHostname = "geomarkettest.redis.cache.windows.net"
# myPassword = "HwOZLrDVNGbR3DZzQS48tUcOrBGcZyrg4AzCaPIfEpg="

# r = redis.StrictRedis(host=myHostname, port=6380,
#                       password=myPassword, ssl=True)


# FLASK CACHE INIT
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

useGeofenceV1 = False

servicebus_client = ServiceBusClient.from_connection_string(conn_str=AZURE_SERVICE_BUS_CONN_STR, logging_enable=True)
servicebus_mgmt_client = ServiceBusAdministrationClient.from_connection_string(AZURE_SERVICE_BUS_CONN_STR)

ALL_TOPICS = set([])
with servicebus_mgmt_client:
    for topic_properties in servicebus_mgmt_client.list_topics():
        ALL_TOPICS.add(topic_properties.name)



# 

USER_TAGS = set([])

# flag if test db is partitioned on city/category
is_city_partitioned = True

leader = redis.Redis(host=leaderip, port=9851)
follower = redis.Redis(host=followerip, port=9851)

NEARBY_POSTS_WS = None

NOTIF_BATCH_SIZE = 2
TOTAL_NOTIF_MAX = 2

RADIUS_THRESHOLD_IN_M = 10000

# NLTK
nltk.download('omw-1.4')

SESSION_TYPE = 'redis'

# sess = Session()
# sess.init_app(app)

SESSION_IP_OBJECT = geocoder.ip('me')
IP_LAT, IP_LON = SESSION_IP_OBJECT.latlng
IP_CITY = SESSION_IP_OBJECT.city


# tmp
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #this is to set our environment to https because OAuth 2.0 only supports https environments

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")  #set the path to where the .json file you got Google console is

flow = Flow.from_client_secrets_file(  #Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],  #here we are specifing what do we get after the authorization
    redirect_uri="http://127.0.0.1:5000/callback"  #and the redirect URI is the point where the user will end up after the authorization
    # redirect_uri="https://locationmarketplacedev.azurewebsites.net/callback"  #and the redirect URI is the point where the user will end up after the authorization

)

def login_is_required(function):  #a function to check if the user is authorized or not
    def wrapper(*args, **kwargs):
        if "google_id" not in session:  #authorization required
            return abort(401)
        else:
            return function()

    return wrapper


@app.route("/login")  #the page where the user can login
def login():
    authorization_url, state = flow.authorization_url()  #asking the flow class for the authorization (login) url
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")  #this is the page that will handle the callback process meaning process after the authorization
def callback():
    flow.fetch_token(authorization_response=request.url)

    # if not session["state"] == request.args["state"]:
    #     abort(500)  #state does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")  #defing the results to show on the page
    auth_name = session["google_name"] = id_info.get("name")

    user_id = hashlib.md5(str(auth_name).encode()).hexdigest()
    session["CURR_USER"] = user_id

    return redirect("/home")  #the final page where the authorized users will end up


@app.route("/logout")  #the logout page and function
def logout():
    session.clear()
    return redirect("/")


# @app.route("/login")  #the home  page where the login button will be located
def f():
    return " <a href='/login'><button>Login</button></a>"

@app.route("/action")
def action():
    try:
        if session['CURR_USER'] != 'NA':
            return redirect("/logout")
        else:
            return redirect("/login")
    except:
        return redirect("/login")



@app.route("/protected_area")  #the page where only the authorized users can go to
@login_is_required
def protected_area():
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"  #the logout button 


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

# Listen to nearby posts for 
def activate_nearby_ws(user_id, radius_in_m=1000):
    try:
        ws = create_connection(f"ws://{leaderip}:9851/NEARBY+users+Match+{user_id}+FENCE+ROAM+posts+*+{radius_in_m}")
        LOGGER.info("Listening to geofence notifications")
        return ws
    except Exception as e:
        LOGGER.warn(e)
        return None


def get_posts_by_id(id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.id=@id",
    parameters=[
        { "name":"@id", "value": id }
    ],
        enable_cross_partition_query=True
    ))
    return items


def get_posts_by_id_list(idList):
    items = list(cos_container.query_items(
            query=f"SELECT * FROM r WHERE ARRAY_CONTAINS(@ids, r.id)",
            parameters=[
                { "name":"@ids", "value": idList}
                        ],
            enable_cross_partition_query=is_city_partitioned
            ))
    return items



# @cache.cached()
# def notifs(radius): 
#     session['CURR_USER'] = "69bd0823d287fbe035d068e3d4d22596"
#     user_id = session["CURR_USER"]
#     radius = int(radius)
#     radius_in_m = min(int(radius), RADIUS_THRESHOLD_IN_M)
#     return render_template("notifs_v2.html", user_id=user_id, radius = radius_in_m, host = f"{leaderip}:9851")


@app.route('/monitor/<radius>', methods=["GET", "POST"])
def view_notifs(radius):
    # session['CURR_USER'] = "69bd0823d287fbe035d068e3d4d22596"
    user_id = session['CURR_USER']
    if request.method == "GET":
        session["socket_url"] = f'ws://{leaderip}:9851/NEARBY+users+Match+{user_id}+FENCE+ROAM+posts+*+{radius}'
        return render_template('notifs_loader.html', radius=radius, url = session["socket_url"], posts = [], user_id = user_id, host = f'{leaderip}:9851')
    else:
        val = request.json.get('notif_batch')
        post_objs = render_notifs(val, make_ref=True)
        return jsonify(post_objs)



def render_notifs(val, make_ref = False):
    rendering = []
    for post in val:
        if type(post) == str:
            post = json.loads(post)
        output = {}
        read=get_posts_by_id(post['id'])[0]
        try:
            try:
                img = ast.literal_eval(read['blob_id'])[0]
                img = get_img_url_with_container_sas_token(img)
                output['img'] = img
            except Exception as e:
                output['img'] = ''
            name = read['title']
            output['name'] = name
            desc = read['descr']
            output['descr'] = desc
            output['id'] = read['id']
            if make_ref:
                output['item_ref'] = url_for('item', item_id = read['id'])
            rendering += [output]
        except Exception:
            continue

    return rendering

    
def create_sbus_topics(topics):
    lat, lon = get_user_pos(session['CURR_USER'])
    city = session['city']
    # city = reverse_geocode.search(lat, lon)['city']
    # city = 'Ithaca'
    res = []
    with servicebus_mgmt_client as mgmt_cl:
        for topic in topics:
            name = f"{city}_{topic}"
            res.append(name)
            try:
                if name not in ALL_TOPICS:
                    mgmt_cl.create_topic(name)
                    ALL_TOPICS.add(name)
                if topic not in ALL_TOPICS:
                    mgmt_cl.create_topic(topic)
                    ALL_TOPICS.add(topic)
            except:
                continue
    mgmt_cl.close()
    return res


def publish_post_to_topic(post, tag):
    res = create_sbus_topics([tag]) + [tag]
    print("res",res)
    with servicebus_client:
        for topic in res:
        # get a Topic Sender object to send messages to the topic
            sender = servicebus_client.get_topic_sender(topic_name=topic)
            with sender:
                sender.send_messages(ServiceBusMessage(post.get('name', ""),application_properties=post))
                print("MESSAGE")
            sender.close()
    servicebus_client.close()


def create_sbs_subscription(tags):
    user_id = session['CURR_USER']
    lat, lon = get_user_pos(user_id)
    # city = reverse_geocode.search(lat, lon)['city']
    # city = 'Ithaca'
    city = session['city']
    with servicebus_mgmt_client as mgmt_cl:
        for tag in tags:
            topic = f"{city}_{tag}"
            sub = f"{user_id}_{tag}"
            try:
                mgmt_cl.create_subscription(topic, sub)
                mgmt_cl.create_subscription(tag, sub)
            except:
                continue
    mgmt_cl.close()


def get_subscription_msgs(tags, same_city = True):
    session['CURR_USER']  = "69bd0823d287fbe035d068e3d4d22596"
    user_id = session['CURR_USER']
    lat, lon = get_user_pos(user_id)
    # city = reverse_geocode.search(lat, lon)['city']
    city = session['city']
    # city = 'Ithaca'
    res = defaultdict(list)
    with servicebus_client:
        for tag in tags:
            topic = tag
            if same_city:
                topic = f"{city}_{tag}"
            subscription = f"{user_id}_{tag}"
            receiver = servicebus_client.get_subscription_receiver(
                topic_name=topic,
                subscription_name=subscription
            )
            with receiver:
                received_msgs = receiver.receive_messages(max_message_count=10, max_wait_time=5)
                for msg in received_msgs:
                    if msg is not None and msg.application_properties is not None:
                        post_obj = {}
                        print()
                        for k, v in msg.application_properties.items():
                            if type(v) == bytes:
                                v = v.decode('utf-8')
                            post_obj[k.decode('utf-8')] = v
                        res[topic].append(post_obj)
                    receiver.complete_message(msg)
    
    servicebus_client.close()
    return res

@app.route('/sub/<tags>')
def sub(tags):
    if '+' not in tags:
        tags = [tags]
    else:
        tags = tags.split('+')
    
    tags_2 = []
    for t in tags:
        if t not in USER_TAGS:
            tags_2.append(t)
            USER_TAGS.add(t)
    create_sbs_subscription(tags)
    return redirect("/home")


@app.route('/watch_tags/<tags>')
@app.route('/watch_tags/<tags>/<city>')
def watch(tags, city = ""):
    same_city = (city == "")
    if '+' not in tags:
        tags = [tags]
    else:
        tags = tags.split('+')
    res = get_subscription_msgs(tags, same_city)
    return jsonify(res)



def activate_notifs(category):
    category = str(category)
    NEARBY_POSTS_WS = activate_nearby_ws(session["CURR_USER"])
    if NEARBY_POSTS_WS is None:
        LOGGER.error("Could not create realtime geofence listener")
        return redirect("/post")
    notif_count = 0
    notif_batch = []
    user_id = session["CURR_USER"]
    lat, lon = get_user_pos(user_id)
    upsert_user_pos(user_id, lat, lon)

    with servicebus_client:
        sender = servicebus_client.get_topic_sender(topic_name=f"{category}")
        with sender:
            notif_batch = []
            batch_message = sender.create_message_batch()
            while True:
                data = NEARBY_POSTS_WS.recv()
                data = process_ws_res(data, category)
                if data is None:
                    continue
                else:
                    # found nearby post in with <category>
                    notif_batch.append(data) 
                    try:
                        batch_message.add_message(ServiceBusMessage(json.dumps(data)))
                    except ValueError as v:
                        LOGGER.warn(v)
                        LOGGER.info("Creating new service bus batch")
                        batch_message = sender.create_message_batch()
           
                    notif_count += 1
                    if notif_count % NOTIF_BATCH_SIZE:
                        session[f"{category}_post_objs"] = notif_batch
                        sender.send_messages(batch_message)
                        notif_batch = []
                    
                    if notif_count == TOTAL_NOTIF_MAX:
                        sender.send_messages(batch_message)
                        break
    
    servicebus_client.close()
    return redirect('/post')


def get_nearby_posts(src_lat, src_lng, city, category, radius=1000):
    search_res = nearby_posts(src_lat, src_lng, radius, category="")

    if search_res == {} or useGeofenceV1:
        DIST_THRESH_IN_KM = 5
        candidate_posts = []
        if category is None:
            candidate_posts = get_posts_by_city(city)
        else:
            candidate_posts = get_posts_by_city_and_category(city, category)

        res = {"closest": [], "further": []}

        for post in candidate_posts:
            post = dict(post)
            # if check_geofence(lat, lng, post.get("fence_udid")) :
            target_lat, target_lng = post.get(
                "target_lat", -1), post.get("target_lng", -1)
            if target_lat != -1:
                dist = check_within_latlng_500(
                    src_lat, src_lng, target_lat, target_lng)
                if dist <= DIST_THRESH_IN_KM:
                    res["closest"].append((post, dist))
                else:
                    res["further"].append((post, dist))

        res["closest"].sort(key=lambda x: x[1])
        res["further"].sort(key=lambda x: x[1])

        cache.set("local-feed", res)

    else:
        ids = search_res.get('idList')
        items = get_posts_by_id_list(ids)
    return items


def near_cached_coords(src_lat, src_lng):
    latest_lat, latest_lng = cache.get("latest_lat"), cache.get("latest_lng")
    if latest_lat is None:
        return False
    if math.round(check_within_latlng_500(src_lat, src_lng, latest_lat, latest_lng)) <= 1:
        return True


@login_is_required
@app.route('/local-feed')
@app.route('/local-feed/<radius>')
def get_local_feed(radius=1000):
    category = request.args.get('category', None)
    user_id = session["CURR_USER"]
    src_lat, src_lng = get_user_pos(user_id)
    city = session['city']

    if radius is not None:
        radius = int(radius)

    if near_cached_coords(src_lat, src_lng):
        res = cache.get("local-feed")
        if res:
            return res

    cache.set("latest_coords", (src_lat, src_lng))
    cache.set("latest_city", city)

    res = get_nearby_posts(src_lat, src_lng, city, category, radius)

    rendering = []
    location_string = f'Looking at posts with {radius} meters of your current location'
    for post in res:
        output = {}
        # read = cos_container.read_item(str(i), partition_key=city)
        read = post
        try:
            try:
                img = ast.literal_eval(read['blob_id'])[0]
                img = "https://geomarketmedia.azureedge.net/media/"+str(img)
                output['img'] = img
            except:
                output['img'] = ''
            name = read['title']
            output['name'] = name
            desc = read['descr']
            output['descr'] = desc
            output['id'] = read['id']
            rendering += [output]
        except:
            continue

    return render_template('local_feed.html', posts=rendering, location=location_string, other_home_link=url_for('home_all'), host=f"{leaderip}:9851", user_id=user_id)


# HOME PAGE
@app.route('/')
@app.route('/home')
def home():

    client_ips = request.headers.get('X-Forwarded-For', request.remote_addr)
    client_ips = client_ips.split(':')[0]

    if client_ips is None or client_ips == '127.0.0.1':
        print('is none')
        client_ips = SESSION_IP_OBJECT.ip
    

    LOGGER.info('Request for home page received')
    try:
        user_id = session['CURR_USER']
        if user_id != 'NA':
            action = "Logout"
            action_item = "logout"
        else:
            action = "Login"
            action_item = "login"
    except:
        session['CURR_USER'] = 'NA'
        user_id = session['CURR_USER']
        action = "Login"
        action_item = "login"

    # Upsert curr user into GeoSVC
    # upsert_user_pos(user_id, IP_LAT, IP_LON)

    city = session['city'] = IP_CITY = geocoder.ip(str(client_ips)).city
    LOGGER.info(IP_CITY)

    recent = read_recent()  # strcture = id=recent, last = last one, recents = values
    # print(recent)
    recents = recent['recents']
    recents = ast.literal_eval(recents)
    # print(recents)
    # print(recents[0])
    print(recents)

    last = int(recent['last'])-1
    recents = recents[last:] + recents[:last]
    rendering = []
    location_string = f'Looking at items from: {city}'
    for i in recents:
        output = {}
        # read = cos_container.read_item(str(i), partition_key=city)
        read=get_post_by_id(i)
        try:
            if read['city'] != city:
                continue
            try:
                img = ast.literal_eval(read['blob_id'])[0]
                img = "https://geomarketmedia.azureedge.net/media/"+str(img)

                # img = "https://geomarketmedia.azureedge.net/media/"+str(img)
                output['img'] = img
            except:
                output['img'] = ''
            name = read['title']
            output['name'] = name
            desc = read['descr']
            output['descr'] = desc
            output['id'] = i
            rendering += [output]
        except:
            continue

    return render_template('home.html', recent=rendering, location = location_string, 
        other_home = "All Recent Items", other_home_link = url_for('home_all'), host = f"{leaderip}:9851", user_id = user_id,
        action=action, action_item= action_item)


@app.route('/home/all')
def home_all():
    print('Request for home page received')
    rendering = []
    
    #    print(recents)
    #    print(recents[0])
    try:
        user_id = session['CURR_USER']
        action = "Logout"
        action_item = "logout"
    except:
        session['CURR_USER'] = 'NA'
        user_id = session['CURR_USER']
        action = "Login"
        action_item = "login"

    recent = read_recent()  # strcture = id=recent, last = last one, recents = values
    #    print(recent)
    recents = recent['recents']
    recents = ast.literal_eval(recents)

    last = int(recent['last'])-1
    recents = recents[last:] + recents[:last]
    rendering = []
    for i in recents:
        output = {}
        read = get_posts_by_id(i)[0]
        try:
            img = ast.literal_eval(read['blob_id'])[0]
            img = "https://geomarketmedia.azureedge.net/media/"+str(img)
            output['img'] = img
        except:
            output['img'] = ''
        name = read['title']
        output['name'] = name
        desc = read['descr']
        output['descr'] = desc
        output['id'] = i
        rendering += [output]

    return render_template('home.html', recent=rendering, other_home="Local Items", other_home_link= url_for('home'), host = f"{leaderip}:9851", user_id = session["CURR_USER"],
     action=action, action_item= action_item)

    

## POSTING

@app.route('/post')
# @cache.cached()
def index():
    print(session)
    try:
        if session['CURR_USER'] == 'NA':
            return redirect('/')
    except:
        return redirect('/')
        
    LOGGER.info('Request for index page received')
    client_ips = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(request.headers)
    print(client_ips)
    print(request.remote_addr)
    client_ips = client_ips.split(':')[0]
    if client_ips is None or client_ips == '127.0.0.1':
        print('is none')
        client_ips = SESSION_IP_OBJECT.ip
    # else:
    #     client_ips = client_ips[0]
    msg=session.get('msg')
    print(msg)
    if msg is None:
        msg= '' 
    print(msg)
    session['msg'] = ''
    # session['name'] = ''
    print("ip:", client_ips)

    # city = IP_CITY
    # session['city'] = city
        
    LOGGER.info('session message reset')
    return render_template('index.html', msg=msg, host = f"{leaderip}:9851", user_id = session["CURR_USER"])


@app.route('/hello', methods=['POST'])
def hello():
    name = request.form.get('name')
    comment = request.form.get('freeform') 
    img = request.form.getlist('files[]')
    # session['name'] = name
    user_id = session.get("CURR_USER")
    (lat, lon) = get_user_pos(user_id)
    city = session['city']
    if name and comment:
        LOGGER.info('Request for hello page received with name=%s' % name)
        contact = request.form.get('contact')
        global post_id
        tags = text_analytics_client.extract_key_phrases([comment])[0]
        if not tags.is_error:
            # print("\tKey Phrases:")
            tag = []
            for phrase in tags.key_phrases:
                tag += [phrase]
            tags = [{"tag" : phrase} for phrase in tag]
        else:
            tags = ''
        post = {
            "name" : name,
            "comment":comment,
            "city": city,
            "target_lat" : lat,
            "target_lng" : lon,
            "user_id" : user_id,
            "tags": tags,
            "contact": contact

        }
        post_id = insert_container(post)

        # Upsert into GeoSVC
        upsert_post(post_id, lat, lon)

    #    def upload(img):
        # global post_id
        print('post2')
        # if request.method == 'POST':
        print('post1')
        print("img", img)
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
                    blob_id = id.hexdigest()+'.' + \
                        file.filename.rsplit('.', 1)[1]
                    blob_client = blob_service_client.get_blob_client(
                        container=blob_container, blob=blob_id)
                    filename = secure_filename(file.filename)
                    file.save(filename)
                    file_names.append(blob_id)
                    with open(filename, "rb") as data:
                        try:
                            blob_client.upload_blob(data, overwrite=True)
                            # rediscnfg.r.set(blob_id, )
                            metadata['filename'] = file.filename
                            blob_client.set_blob_metadata(
                                {"filename": file.filename})
                            img_url = "https://geomarketmedia.azureedge.net/media/"+str(blob_id)
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
                # item_name = session.get('name')

                # msg = item_name + " has been uploaded to the server!"
                os.remove(filename)
            print(tags)
            tags = [{"tag": tag} for tag in tags]
            update_container_pic(post_id, file_names)
            update_container_tags(post_id, tags)
            update_recent(post_id)
            session["msg"] = msg

            return redirect(url_for('home', host=f"{leaderip}:9851", user_id=session["CURR_USER"]))
            # render_template("index.html", msg=msg)
        else:
            session["msg"] = 'No pics provided.'
            print(session["msg"])
            return redirect(url_for('index', host=f"{leaderip}:9851", user_id=session["CURR_USER"]))
            # render_template("index.html", msg='No pics provided.')
       

    #    return redirect(url_for('home', host=f"{leaderip}:9851", user_id=session["CURR_USER"]))
    else:
        LOGGER.info('Request for hello page received with no name or comment -- redirecting')
        return redirect(url_for('index'))



blob_service_client = BlobServiceClient.from_connection_string(
    blob_connect_str)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in blob_allowed_ext

# @app.route('/upload',methods=['POST'])






#QUERYING 

@app.route('/query')
def query():
   LOGGER.info('Request for query page received')
   return render_template('query.html', host = f"{leaderip}:9851", user_id = session["CURR_USER"])


@app.route('/query_load', methods=['POST', 'GET'])
def query_load():
    if request.method == "POST":
        item = request.form.get('itm')
        read = cos_container.read_item(str(item), partition_key=str(item))
        files = ast.literal_eval(read['blob_id'])
        img1 = img2 = img3 = img4 = ''
        try:
            img1 = get_img_url_with_container_sas_token(files[0])
            img2 = get_img_url_with_container_sas_token(files[1])
            img3 = get_img_url_with_container_sas_token(files[2])
            img4 = get_img_url_with_container_sas_token(files[3])
        except:
            pass
        # , ButtonPressed=ButtonPressed)
        return render_template("query_load.html", id=item,  img1=img1, img2=img2, img3=img3, img4=img4)
    # , ButtonPressed = ButtonPressed)
    return render_template("query_load.html", id='error', host=f"{leaderip}:9851", user_id=session["CURR_USER"])


@app.route('/query_results', methods=['POST'])
def query_results():
    LOGGER.info('query_load')

    if request.method == "POST":
        term = request.form.get('input')
        forms = get_word_forms(term)['n']
        items = []
        for f in forms:
            items += get_posts_by_category(f)

        rendering = []
        for i in items:
            output = {}

            read = i
            try:
                img = ast.literal_eval(read['blob_id'])[0]
                img = "https://geomarketmedia.azureedge.net/media/"+str(img)
                output['img'] = img
            except:
                output['img'] = ''
            name = read['title']
            output['name'] = name
            desc = read['descr']
            output['descr'] = desc
            output['id'] = i['id']
            rendering += [output]

        return render_template("query_results.html", query_key=term, recent = rendering)  # , ButtonPressed=ButtonPressed)
    return render_template("query_load.html", id='error', host = f"{leaderip}:9851", user_id = session["CURR_USER"])  # , ButtonPressed = ButtonPressed)



## AZURE QUERYING/DATABASE FUNCTIONS

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




@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
global post_id
post_id = 0




### ITEM PAGES

@app.route('/item/<item_id>')
def item(item_id):
    read = get_posts_by_id(item_id)[0]
    try:
        imgs = ast.literal_eval(read['blob_id'])
        url_img = []
        for img in imgs:
            url_img += ["https://geomarketmedia.azureedge.net/media/"+str(img)]
    except:
        url_img = []
    curr_desc = read['descr']
    curr_name = read['title']
    curr_city = read['city']

    tag0=''
    contact = 'None.'
    try:
        tags = read.get('tags')
        tag0 = tags[0]
        if tags is not None:
            # tags = ast.literal_eval(tags)
            tags = str(tags)
        contact = read.get('contact')
    except:
        tags= ''
    print("tag0", tag0)
    try: 
        result = ml_call(tag0['tag'])
        result = result.decode()
        # print(result)
        # print(result.decode())

        # print(type(result))
        # print(result[0])


        item1=get_posts_by_category(result[0])
        print(item1)
        item2=get_posts_by_category(result[1])
        item3=get_posts_by_category(result[2])
        recents = item1+item2+item3
        random.shuffle(recents)
        # if len(recents) > 3:
        #     recents=recents[:3]
        
        print(recents)
        j = 0
        rendering = []
        for i in recents:
            if j >= 3:
                break
            output = {}
            # read = cos_container.read_item(str(i), partition_key=city)
            read=i
            try:
                if read['city'] != curr_city:
                    continue
                try:
                    img = ast.literal_eval(read['blob_id'])[0]
                    img = "https://geomarketmedia.azureedge.net/media/"+str(img)

                    # img = "https://geomarketmedia.azureedge.net/media/"+str(img)
                    output['img'] = img
                except:
                    output['img'] = ''
                name = read['title']
                if curr_name == name:
                    continue
                output['name'] = name
                desc = read['descr']
                output['descr'] = desc
                output['id'] = i['id']
                rendering += [output]
                j += 1
            except:
                continue
            print()
            print("RENDeriNG", rendering)
            rcmd = 'Here are some local suggestions:'

            if len(rendering)== 0:
                # rendering 
                rcmd = 'No recommendations.'
    except:
        rendering = []
        rcmd = 'No recommendations.'
    
    return render_template('item.html', itemname = curr_name, desc = curr_desc, contact = contact,  rcmd = rcmd, pics_list = url_img, tags = tags, dict=rendering, city = curr_city, host = f"{leaderip}:9851", user_id = session["CURR_USER"])


##ML


def allowSelfSignedHttps(allowed):
    # bypass the server certificate verification on client side
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context

    allowSelfSignedHttps(True) # this line is needed if you use self-signed certificate in your scoring service.

    # Request data goes here
    # The example below assumes JSON formatting which may be updated
    # depending on the format your endpoint expects.
    # More information can be found here:
    # https://docs.microsoft.com/azure/machine-learning/how-to-deploy-advanced-entry-script
def ml_call(term):
    data = {"data":[term]}

    body = str.encode(json.dumps(data))

    url = 'http://ae6f509c-19cf-4335-bd42-6a74ab9f4adb.eastus.azurecontainer.io/score'
    # Replace this with the primary/secondary key or AMLToken for the endpoint
    # api_key = ''
    # if not api_key:
    #     raise Exception("A key should be provided to invoke the endpoint")

    # The azureml-model-deployment header will force the request to go to a specific deployment.
    # Remove this header to have the request observe the endpoint traffic rules
    # headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer ')}


    req = urllib.request.Request(url, body, headers)

    try:
        response = urllib.request.urlopen(req)

        result = response.read()
        return result
    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))

        # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
        print(error.info())
        print(error.read().decode("utf8", 'ignore'))
        return "failed"




## AZURE CONTAINER OPS

def insert_container(post,picture_id=''):
    title = post["name"]
    desc = post["comment"]
    city = post["city"]
    user_id = session["CURR_USER"]
    id = hashlib.md5(str(title).encode()).hexdigest()
    id = 'item'+id
    cos_container.upsert_item({
        'id':'{0}'.format(id),
        'user_id' : user_id,
        'city' : city,
        "target_lat": post["target_lat"],
        "target_lng": post["target_lng"],
        'title' : '{0}'.format(str(title)),
        'descr' : '{0}'.format(str(desc)),
        'blob_id': '{0}'.format(str(picture_id)),
        'tags' : post['tags'],
        'contact' : post['contact']

    })
    return id

def update_container_pic(item, picture_id=''):
    print(str(item))
    read = cos_container.read_item(str(item), partition_key=str(session["city"]))
    cos_container.upsert_item({
        'id':'{0}'.format(item),
        'user_id': read['user_id'],
        'city' : read['city'],
        "target_lat": read["target_lat"],
        "target_lng": read["target_lng"], 
        'title' : '{0}'.format(read['title']),
        'descr' : '{0}'.format(read['descr']),
        'blob_id': '{0}'.format(str(picture_id)),
        'tags': read['tags'],
        'contact' : read['contact']


    })
    return id

def update_container_tags(item,tags=''):
    read = cos_container.read_item(
        str(item), partition_key=str(session["city"]))
    cos_container.upsert_item({
        'id':'{0}'.format(item),
        'user_id': read['user_id'],
        'title' : '{0}'.format(read['title']),
        'descr' : '{0}'.format(read['descr']),
        'city' : read["city"],
        "target_lat": read["target_lat"],
        "target_lng" : read["target_lng"],
        'blob_id': '{0}'.format(read['blob_id']),
        'tags': read['tags'] + tags,
        'contact' : read['contact']

    })
    # publish to service bus topic
    publish_post_to_topic(read, str(tags[0]['tag']))
    return id


def get_posts_by_seller_id(seller_id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.user_id=@id  ORDER BY r._ts DESC",
    parameters=[
        { "name":"@id", "value": seller_id }
    ],
        enable_cross_partition_query=True
    ))
    return items

def get_posts_by_id(id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.id=@id  ORDER BY r._ts DESC",
    parameters=[
        { "name":"@id", "value": id }
    ],
        enable_cross_partition_query=True
    ))
    return items

def get_posts_by_id_list(idList):
    items = list(cos_container.query_items(
            query=f"SELECT * FROM r WHERE ARRAY_CONTAINS(@ids, r.id)  ORDER BY r._ts DESC",
            parameters=[
                { "name":"@ids", "value": idList}
                        ],
            enable_cross_partition_query=is_city_partitioned
            ))
    return items


@cache.memoize(50)
def get_posts_by_city(city):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.city=@city  ORDER BY r._ts DESC",
    parameters=[
        { "name":"@city", "value": city }
    ],
        enable_cross_partition_query=is_city_partitioned
    ))
    print(len(items))
    return items


@cache.memoize(50)
def get_posts_by_city_and_category(city, category):
    items = list(cos_container.query_items(
        query="SELECT * FROM r WHERE r.city=@city AND (exists(select value t from t in r.tags where Contains(lower(t.tag), lower(@category))) OR Exists(select * from r.title where  Contains(lower(r.title), lower(@category))) OR Exists(select * from r.descr where  Contains(lower(r.descr), lower(@category))))  ORDER BY r._ts DESC",
    parameters=[
        { "name":"@city", "value": city },
        { "name":"@category", "value": category },
    ],
        enable_cross_partition_query=is_city_partitioned
    ))
    return items


@cache.memoize(50)
def get_posts_by_category(category):
    items = list(cos_container.query_items(
        query="SELECT * FROM r WHERE exists(select value t from t in r.tags where Contains(lower(t.tag), lower(@category))) OR Exists(select * from r.title where  Contains(lower(r.title), lower(@category))) OR Exists(select * from r.descr where  Contains(lower(r.descr), lower(@category)))  ORDER BY r._ts DESC ",
    parameters=[
        { "name":"@category", "value": category },
    ],
        enable_cross_partition_query=True
    ))
    return items


def get_post_by_id(post_id):
    items = list(cos_container.query_items(
    query="SELECT * FROM r WHERE r.id=@id ORDER BY r._ts DESC",
    parameters=[
        { "name":"@id", "value": post_id }
    ],
        enable_cross_partition_query=True
    ))
    return items[0]

def read_recent():
    user_id = session["CURR_USER"]
    src_lat, src_lng = get_user_pos(user_id)
    if near_cached_coords(src_lat, src_lng):
        res = cache.get("local_recent")
        LOGGER.info("Getting Cached Local Recent posts")
        if res is not None:
            return res
    
    res = cos_container.read_item(('recent'), partition_key='recent')
    cache.set("local_recent", res)
    return res

def update_recent(new_item):
    try:
        read = read_recent()
        print('read')
        last = (int(read['last']) + 1) % 9
        print('last')
        recents = read['recents']
        recents = ast.literal_eval(recents)
        print('recents', recents)
        print('last', last)

        print('list')
        if len(recents) == 9:
            recents[last] = new_item
        elif new_item in recents:
            pass
        else:
            recents.append(new_item)
        cos_container.upsert_item({
        'id':'{0}'.format('recent'),
        'last' : '{0}'.format(last),
        'recents':'{0}'.format(recents),
        'city': 'recent'
    }) 
        print('sucess')
    except:
        last = 0
        recents = [new_item]
        cos_container.upsert_item({
        'id':'{0}'.format('recent'),
        'last' : '{0}'.format(last),
        'recents':'{0}'.format(recents) ,
        'city':'recent'
    })
        print('failed123')

        

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
    app.run(host="0.0.0.0", debug=True)
    leader.close()
    follower.close()
