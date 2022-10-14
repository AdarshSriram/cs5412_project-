import requests, json, os, time
from dotenv import load_dotenv



load_dotenv()

maps_key = os.environ['MAPS_KEY']
coords = [-80.978996, 35.094341]

geofence_udid = ''

def upload_geofence():
    global geofence_udid
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
            "radius": 5000
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

def check_geofence(lat, lon):
    check_geofence_url = 'https://atlas.microsoft.com/spatial/geofence/json'
    print(geofence_udid)
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
    print()
    print(response_json)
    print('Event published:', response_json.get('isEventPublished'))
    print('Distance to geofence:', response_json['geometries'][0]['distance'])
    print('Nearest geofence location', response_json['geometries'][0]['nearestLon'], ',', response_json['geometries'][0]['nearestLat'])
    print()


    if response_json['geometries'][0]['distance'] < 0:
      print("Buyer is inside geofence")
    else:
      print("buyer is outside geofence")


    


upload_geofence()
check_geofence(coords[0], coords[1])