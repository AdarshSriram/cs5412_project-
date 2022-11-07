from datetime import datetime, timedelta
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient,generate_container_sas, ContainerSasPermissions
import hashlib
import os
import requests
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
import ast

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

@app.route('/query')
def query():
   print('Request for query page received')
   return render_template('query.html')

# using generate_container_sas
def get_img_url_with_container_sas_token(blob_name):
    container_sas_token = generate_container_sas(
        account_name=blob_account,
        container_name=blob_container,
        account_key=blob_key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    blob_url_with_container_sas_token = f"https://{blob_account}.blob.core.windows.net/{blob_container}/{blob_name}?{container_sas_token}"
    return blob_url_with_container_sas_token


@app.route('/query_load', methods=['POST','GET'])
def query_load():
    print('query_load')
    if request.method == "POST":
        item = request.form.get('itm')
        read = cos_container.read_item(str(item), partition_key=str(item))
        files = ast.literal_eval(read['blob_id'])
        # for file in files:
        img1 = img2 = img3 = img4 = ''
        try: 
            img1 = get_img_url_with_container_sas_token(files[0])
            img2 = get_img_url_with_container_sas_token(files[1])
            img3 = get_img_url_with_container_sas_token(files[2])
            img4 = get_img_url_with_container_sas_token(files[3])
        except:
            pass


        return render_template("query_load.html", id=item,  img1=img1, img2 = img2, img3=img3, img4=img4)#, ButtonPressed=ButtonPressed)
    return render_template("query_load.html", id = 'error')#, ButtonPressed = ButtonPressed)

# if request.method == "POST":
        # I think you want to increment, that case ButtonPressed will be plus 1.


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
global post_id
post_id = 0

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')
   comment = request.form.get('freeform') 
   print(comment)
   if name and comment:
       print('Request for hello page received with name=%s' % name)
       global post_id
       post_id = insert_container(name+ ' ' + comment)
       return render_template('hello.html', name = name, comment = comment)
   else:
       print('Request for hello page received with no name or comment -- redirecting')
       return redirect(url_for('index'))




def insert_container(item,picture_id=''):
    id = hashlib.md5(str(item).encode()).hexdigest()
    id = 'item'+id
    cos_container.upsert_item({
        'id':'{0}'.format(id),
        'test1' : 'test',
        'field' : '{0}'.format(str(item)),
        'blob_id': '{0}'.format(str(picture_id))
    })
    return id

def update_container(item,picture_id=''):
    print(str(item))
    read = cos_container.read_item(str(item), partition_key=str(item))
    cos_container.upsert_item({
        'id':'{0}'.format(item),
        'test1' : 'test',
        'field' : '{0}'.format(read['field']),
        'blob_id': '{0}'.format(str(picture_id))
    })
    return id

blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in blob_allowed_ext

@app.route('/upload',methods=['POST'])
def upload():
    global post_id
    print('post2')
    if request.method == 'POST':
        print('post1')
        img = request.files.getlist('files[]')
        if len(img) > 0:
            file_names = []
            print('hgello123')
            msg = 'Uploading'
            for file in img:
                print(file.filename)
                if file and allowed_file(file.filename):
                    id = hashlib.md5(str(file.filename).encode())
                    blob_id = id.hexdigest()+'.'+file.filename.rsplit('.', 1)[1]
                    blob_client = blob_service_client.get_blob_client(
                        container=blob_container, blob=blob_id)
                    filename = secure_filename(file.filename)
                    file.save(filename)
                    file_names.append(blob_id)
                    with open(filename, "rb") as data:
                        try:
                            blob_client.upload_blob(data, overwrite=True)
                            blob_client.set_blob_metadata({"filename":file.filename})
                            # blob_service.set_blob_metadata(container_name="mycontainer",
                            #    blob_name="myblob",
                            #    x_ms_meta_name_values={"Meta Century":"Nineteenth","Meta Author":"Mustafa"})


                            # dictToSend = {'question':'what is the answer?'}
                            # put_string = 'https://'+blob_account+'.blob.core.windows.net/'+blob_container+'/myblob?comp=tags'

                            # res = requests.post('https: // myaccount.blob.core.windows.net/mycontainer/myblob?comp=tags
                            #                     ', json=dictToSend)
                            # print 'response from server:',res.text
                        except:
                            print('failed')
                            pass
                msg = "Upload Done!"
                os.remove(filename)
            update_container(post_id, file_names)
            
            return render_template("index.html", msg=msg)
        else:
            return render_template("index.html", msg='No pics provided.')
    else:
        return render_template("index.html", msg='Upload failed.')

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
