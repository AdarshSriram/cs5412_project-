import json
import redis
# from config import REDIS_PASSWD
from pyle38 import Tile38
import asyncio
import json


host = "tile38.9f8830e21cdf4aeba0f6.eastus.aksapp.io"
leaderip = "20.85.191.185"
follower = "40.88.200.96"
host = f"{leaderip}:9851"

def test_tile38():
    client = redis.Redis(host=leaderip, port=9851)
    # insert data
    client.execute_command("""SET test_user adarsh1 field c 1 POINT 0 0""")
    # client.execute_command("""SET user adarsh2 field a 2 POINT 0 0""")
    # client.execute_command("""SET user adarsh3 field a 2 POINT 0 0""")
    client.execute_command("""SET test_post shoe1 field c 2 POINT 0 0""")
    client.execute_command("""SET test_post shoe2 field c 2 POINT 0 0""")
    # r1 =client.execute_command('GET', 'user', 'adarsh1', 'WITHFIELDS')
    # r2 = json.loads(client.execute_command('GET', 'user', 'adarsh1').decode('utf-8'))
    
    r = client.execute_command("NEARBY test_post point 0 0 1000")
    # res = []
    print(r[0])
    print()
    print(r[1])
    print(r[1][0])
    print(r[1][1])
    # for o in r[1]:
    #     print(o[0])
    #     print(o[1])
        # res.append({
        #     "id" : o[0].decode('utf-8'),
        #     "coords" : json.loads(o[1].decode('utf-8'))["coordinates"]
        # })
    # print(res)
    # result2 = client.execute_command("""SETHOOK warehouse https://tile38hook.azurewebsites.net/api/testhook NEARBY fleet FENCE POINT 0 0 500""")
    # print(result2)
    # print()
    # result3 = client.execute_command("""SET fleet bus POINT 33.460 -112.260""")
    # print(result3)


    client.close()


test_tile38()

from websocket import create_connection
import time

def socket_v1():
    # t_end = time.time() + 60
    try:
        ws = create_connection(f"ws://{host}/NEARBY+user+Match+adarshsriram+FENCE+ROAM+post+*+5000")
    except Exception as e:
        print(e)
        return
    while True:
        r =  json.loads(ws.recv())
        if "ok" in r:
            print("Roaming Fence Activated")
            continue
        result = {
            "time" : r.get('time'),
            "user_id" : r.get('id'),
            "coordinates" : r['object']['coordinates'],
            'post_id' : r['nearby']['id'],
            'category_ENUM' : r['nearby']['key'],
            "distance" : r['nearby']['meters']

        }
        
        print(r)

    ws.close()


# socket_v1()


