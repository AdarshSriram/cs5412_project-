from datetime import datetime, timedelta
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient,generate_container_sas, ContainerSasPermissions
import hashlib
import os
import requests
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
import ast
import uuid
import time
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, json, session
from geofence import upload_geofence, check_geofence
import geocoder
import json
from app import *

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


@app.route('/home')
def home():
    print('Request for home page received')
    coords = geocoder.ip("me").latlng
    session["lat"], session["lng"] = coords[0], coords[1]
    session["city"] = geocoder.ip("me").city
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

    return render_template('home.html', recent=rendering, location=location_string,
                           other_home="All Recent Items", other_home_link=url_for('home_all'))
