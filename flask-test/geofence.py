import requests, json, os, time
from dotenv import load_dotenv
import geocoder


load_dotenv()

maps_key = os.environ['MAPS_KEY']


def upload_geofence():
    coords = geocoder.ip("me").latlng
# change from lat, lng to lng, lat
    coords = [coords[1], coords[0]]
    city = geocoder.ip("me").city

    print(f"Curr Lng : {coords[1]} ,  Curr Lat : {coords[0]}")
    print(f'City: {city}')
    print()

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

def check_geofence(lat, lon, geofence_udid):
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
      return True
    else:
      print("buyer is outside geofence")
      return False


    


# upload_geofence(coords)
# check_geofence(coords[0], coords[1])