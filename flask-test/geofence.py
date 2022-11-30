import requests, json, os, time
# from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, asin

import geocoder
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, json, session



# load_dotenv()
app = Flask(__name__)

app.config.from_pyfile('config.py')

maps_key = app.config['MAPS_KEY']


def upload_geofence(coords, city):
#     coords = geocoder.ip("me").latlng
# # change from lat, lng to lng, lat
#     coords = [coords[1], coords[0]]
#     city = geocoder.ip("me").city

#     print(f"Curr Lng : {coords[1]} ,  Curr Lat : {coords[0]}")
#     print(f'City: {city}')
#     print()

    geofence_upload_url = 'https://atlas.microsoft.com/mapData/upload'
    params={
        'subscription-key': maps_key,
        'api-version': '1.0',
        'dataFormat': 'geojson'
    }

    data = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coords
        },
        "properties": {
            "subType": "Circle",
            "geometryId" : "1",
            "radius": 2500
        }
    }]
    }

    geofence_create_response = requests.post(geofence_upload_url, 
                                              params=params, 
                                              json=data)
    geofence_location = geofence_create_response.headers['location']

    response = requests.get(geofence_location, params=params)
    response_json = response.json()

    while 'status' in response_json and response_json['status'] == 'Running':
        time.sleep(0.5)
        response = requests.get(geofence_location, params=params)
        response_json = response.json()
    
    resource_location = response.json()['resourceLocation']
    response = requests.get(resource_location, params=params)

    geofence_udid = response.json()['udid']

    print()
    print('Geofence UDID:', geofence_udid)
    print()

    return response.status_code, geofence_udid, city


def check_within_latlng_500(source_lat, source_lng, target_lat=0, target_lng=0):
    Radius = 6371  # Radius of the earth to nearest km
    lat1 = source_lat
    lat2 = target_lat
    lon1 = source_lng
    lon2 = target_lng
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat / 2) * sin(dLat / 2) + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    c = 2 * asin(sqrt(a))
    return Radius * c

def check_geofence(lat, lon, geofence_udid):
    check_geofence_url = 'https://atlas.microsoft.com/spatial/geofence/json'
    # print(geofence_udid)
    params={
        'subscription-key': maps_key,
        'api-version': '1.0',
        'udid': geofence_udid,
        'lat': lat,
        'lon': lon,
        'deviceId': 'device',
        'searchBuffer': 500,
        'mode': 'EnterAndExit',
        'isAsync': 'False'
    }

    check_geofence_response = requests.get(check_geofence_url, params=params)
    response_json = check_geofence_response.json()
    # print()
    # print(response_json)
    # print('Event published:', response_json.get('isEventPublished'))
    # print('Distance to geofence:', response_json['geometries'][0]['distance'])
    # print('Nearest geofence location', response_json['geometries'][0]['nearestLon'], ',', response_json['geometries'][0]['nearestLat'])
    # print()


    if response_json['geometries'][0]['distance'] < 0:
    #   print("Buyer is inside geofence")
      return True
    else:
    #   print("buyer is outside geofence")
      return False


    


# upload_geofence(coords)
# check_geofence(coords[0], coords[1])
