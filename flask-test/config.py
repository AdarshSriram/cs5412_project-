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
CONTAINER = "SampleDB"
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


# Authenitcation with Google
GOOGLE_CLIENT_ID = "1006873411191-4gd8m83dkokbsjgha2r0i0kbe3l2d94s.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)