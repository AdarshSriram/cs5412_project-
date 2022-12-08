import json
import redis
# from app import IP_LAT, IP_LON, category_hasher
from config import leaderip, followerip

IP_LAT, IP_LON =0, 0

leader = redis.Redis(host=leaderip, port=9851)
follower = redis.Redis(host=followerip, port=9851)

def get_user_pos(user_id):
    try:
        res = follower.execute_command('GET', 'users', user_id).decode('utf-8')
        res = json.loads(res)
        coords = res.get('coordinates')
        return (coords[1], coords[0])
    except Exception as e:
        # LOGGER.warn(e)
        return [IP_LAT, IP_LON]

def get_user_categoryEnum(user_id):
    res =follower.execute_command('GET', 'users', user_id, 'WITHFIELDS')
    return int(res[1][1].decode('utf-8'))


def upsert_user_pos(user_id, lat, lon):
    res=leader.execute_command(f"""SET users {user_id} POINT {lat} {lon}""")
    return res

def update_user_category(user_id, category=1):
    leader.execute_command(f"""FSET users {user_id} category {category}""")

def upsert_post(post_id, lat, lon, category=1):
    res = leader.execute_command(f"""SET posts {post_id} field category {category} POINT {lat} {lon}""")
    return res

def update_post_category(post_id, category=1):
    leader.execute_command(f"""FSET posts {post_id} category {category}""")

def _decode_obj_list(r):
    post_ids = []
    post_items = []
    for o in r[1]:
        coords = json.loads(o[1].decode('utf-8')).get("coordinates")
        post_data = {
            "id" : o[0].decode('utf-8'),
            "lat" : coords[1],
            'lon' : coords[0]
        }
        if len(o) > 2:
            category = o[2][1].decode('utf-8')
            post_data['categoryEnum'] = category

        post_items.append(post_data)
        post_ids.append(post_data['id'])

    return {'items' : post_items, 'idList': post_ids}

def nearby_posts(lat, lon, radius, category = ""):
    r = []
    try:
        if category != "":
            r = follower.execute_command(f"""nearby posts where category {category} point {lat} {lon} {radius}""")
        else:
            r = follower.execute_command(f"""nearby posts point {lat} {lon} {radius}""")     
        return _decode_obj_list(r)
    except Exception as e:
        LOGGER.error(e)
        return {}


# Detect if any user interested in some category comes near post
def set_post_fence(post_id, category):
    postObj = dev_client.execute_command('GET', 'posts', str(post_id), 'WITHFIELDS')
    postObj, category = json.loads(postObj[0].decode('utf-8')), postObj[1][1].decode('utf-8')
    lng, lat = postObj.get('coordinates')
    leader.execute_command(f"sethook notify https://tile38hook.azurewebsites.net/api/testhook NEARBY users Where category {category} FENCE POINT {lat} {lng} 500")
    

def process_ws_res(res, category = ""):
    r =  json.loads(res)
    if "ok" in r:
        print("Roaming Fence Activated")
        return None
    else:
        # post_id = r['nearby']['id']
        # postObj = json.loads(follower.execute_command('GET', 'posts', str(post_id), 'WITHFIELDS'))
        # category_enum = int(postObj['field']['category'])
        # m = category_hasher
        # m.update(category)
        # query_category = str(int(m.hexdigest(), 16))[0:12]
        # if category == '' or query_category != category_enum:
        return {
            "time" : r.get('time'),
            "user_id" : r.get('id'),
            "coordinates" : r['object']['coordinates'],
            'post_id' : r['nearby']['id'],
            'category' : category, 
            "distance" : r['nearby']['meters']
            }
        # else:
        #     return None

    

