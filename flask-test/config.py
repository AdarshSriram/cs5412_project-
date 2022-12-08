import os

# settings = {
#     'host': os.environ.get('ACCOUNT_HOST', 'https://mktplce-fence.documents.azure.com:443/'),
#     'master_key': os.environ.get('ACCOUNT_KEY', 'tx6lvkJ3qZ9JX87Jk2Z7kvSWpXxJPh8ZlfsrOnTbaSyMdq5VxeqNSPSVuerI98sigXXFvIPFEbRXKVSKQc8nlw=='),
#     'database_id': os.environ.get('COSMOS_DATABASE', 'ToDoList'),
#     'container_id': os.environ.get('COSMOS_CONTAINER', 'Items'),
# }
# https://franckess.com/post/uploading-files-azure-blob-flask/
ACCOUNT_NAME = "mktplce-fence"
ACCOUNT_KEY = "tx6lvkJ3qZ9JX87Jk2Z7kvSWpXxJPh8ZlfsrOnTbaSyMdq5VxeqNSPSVuerI98sigXXFvIPFEbRXKVSKQc8nlw=="
CONNECTION_STRING = "AccountEndpoint=https://mktplce-fence.documents.azure.com:443/;AccountKey=tx6lvkJ3qZ9JX87Jk2Z7kvSWpXxJPh8ZlfsrOnTbaSyMdq5VxeqNSPSVuerI98sigXXFvIPFEbRXKVSKQc8nlw==;"
CONTAINER = "Data"
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg'])
MAX_CONTENT_LENGTH = 20 * 1024 * 1024    # 20 Mb limit
URI = "https://mktplce-fence.documents.azure.com:443/"

BLOB_ACCOUNT_NAME = "mktplcemediastre"
BLOB_ACCOUNT_KEY = "5/vuv4b/g0sdPFTDL0Y8hqut1maNpNuaTHfQ59tBs6wZJboJv5RSIad6JbHSLDaxyKSb8vuM1LuC+AStVyh6fw=="
BLOB_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=mktplcemediastre;AccountKey=5/vuv4b/g0sdPFTDL0Y8hqut1maNpNuaTHfQ59tBs6wZJboJv5RSIad6JbHSLDaxyKSb8vuM1LuC+AStVyh6fw==;EndpointSuffix=core.windows.net"
BLOB_CONTAINER = "media"
BLOB_ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg'])
BLOB_MAX_CONTENT_LENGTH = 20 * 1024 * 1024    # 20 Mb limit

CV_KEY = 'b9e10182ec6d45aaab209c666aeb73cb'
CV_ENDPOINT = 'https://projectvisionservice.cognitiveservices.azure.com/'

TEXT_KEY = '606cfd6343ae45ffa352b9959f52507c'
TEXT_ENDPOINT = 'https://geomarket-text.cognitiveservices.azure.com/'


# Authenitcation with Google
GOOGLE_CLIENT_ID = "1006873411191-4gd8m83dkokbsjgha2r0i0kbe3l2d94s.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

REDIS_PASSWD = "PufNGfIGmel6V8NYtm1hjbSU4foQgBSh"

REDIS_HOST = 'redis-10873.c265.us-east-1-2.ec2.cloud.redislabs.com'
REDIS_PORT =10873

leaderip = "20.85.191.185"
followerip = '40.88.200.96'

leaderip_dev = 'localhost'

AZURE_SERVICE_BUS_CONN_STR = "Endpoint=sb://tile38hook.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=n650y/dpF6q97XftWNzwmGvPcOTt/bynlWNpmFpItMo="
