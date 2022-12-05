import json
from app import leader, follower, dev_client



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
    res = []
    for o in r[1]:
        res.append(o[0].decode('utf-8'))
    return res

def nearby_posts(lat, lon, radius, category = ""):
    r = []
    if category != "":
        r = follower.execute_command(f"""nearby posts where category {category} point {lat} {lon} {radius}""")
    else:
        r = follower.execute_command(f"""nearby posts point {lat} {lon} {radius}""")
    
    return _decode_obj_list(r)


# Detect if any user interested in some category comes near post
def set_post_fence(post_id, category):
    postObj = dev_client.execute_command('GET', 'posts', str(post_id), 'WITHFIELDS')
    postObj, category = json.loads(postObj[0].decode('utf-8')), postObj[1][1].decode('utf-8')
    lng, lat = postObj.get('coordinates')
    leader.execute_command(f"sethook notify https://tile38hook.azurewebsites.net/api/testhook NEARBY users Where category {category} FENCE POINT {lat} {lng} 500")
    

# Listen to nearby posts for 
def activate_nearby_ws(user_id, radius_in_m=1000):
    try:
        ws = create_connection(f"ws://{leader}/NEARBY+users+Match+{user_id}+FENCE+ROAM+posts+*+{radius_in_m}")
        return ws
    except Exception as e:
        print(e)
        return None

def process_ws_res(res, category = "testcategory"):
    r =  json.loads(res)
    if "ok" in r:
        print("Roaming Fence Activated")
        return None
    else:
        # post_id = r['nearby']['id']
        # postObj = json.loads(follower.execute_command('GET', 'posts', str(post_id), 'WITHFIELDS'))
        # category_enum = int(postObj['field']['category'])
        # category_str =  DESERIALIZE[category_enum]
        # if category != 'test_category' or category_str != category:
        #     return None
        
        
        # TODO: figure out GET parsing to check category
        return {
            "time" : r.get('time'),
            "user_id" : r.get('id'),
            "coordinates" : r['object']['coordinates'],
            'post_id' : r['nearby']['id'],
            'category' : category, 
            "distance" : r['nearby']['meters']
        }

    

