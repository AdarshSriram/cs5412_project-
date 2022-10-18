from datetime import datetime
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
import hashlib
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, json
app = Flask(__name__)

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

@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')
   comment = request.form.get('freeform') 
   print(comment)
   if name:
       print('Request for hello page received with name=%s' % name)
       insert_container(name+ ' ' + comment)
       return render_template('hello.html', name = name, comment = comment)
   else:
       print('Request for hello page received with no name or blank name -- redirecting')
       return redirect(url_for('index'))




def insert_container(item):
    id = hashlib.md5(str(item).encode())
    cos_container.upsert_item({
        'id':'item{0}'.format(id.hexdigest()),
        'test1' : 'test',
        'field' : '{0}'.format(str(item))
    })

blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in blob_allowed_ext

@app.route('/upload',methods=['POST'])
def upload():
    print('post2')
    if request.method == 'POST':
        print('post1')
        img = request.files['file']
        print('hgello123')
        if img and allowed_file(img.filename):
            print('h23 d d')
            filename = secure_filename(img.filename)
            img.save(filename)
            print('hello')
            blob_client = blob_service_client.get_blob_client(container = blob_container, blob = filename)
            with open(filename, "rb") as data:
                try:
                    blob_client.upload_blob(data, overwrite=True)
                    msg = "Upload Done ! "
                except:
                    pass
            os.remove(filename)
    return render_template("index.html", msg=msg)


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


if __name__ == '__main__':
   app.run()
