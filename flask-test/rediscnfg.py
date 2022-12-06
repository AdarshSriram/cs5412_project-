import redis
import geocoder
import logging
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL, leaderip, followerip, AZURE_SERVICE_BUS_CONN_STR

leader = redis.Redis(host=leaderip, port=9851)
follower = redis.Redis(host=followerip, port=9851)
dev_client = redis.Redis(host="localhost", port=9851)

SESSION_IP_OBJECT = geocoder.ip('me')
IP_LAT, IP_LON = SESSION_IP_OBJECT.latlng
IP_CITY = SESSION_IP_OBJECT.city

LOGGER = logging.getLogger(__name__)

