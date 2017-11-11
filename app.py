import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from facebook_credentials import FacebookCredentials


app = Flask(__name__)
CORS(app)

_test = 'RDS_DB_NAME' not in os.environ
ssl = False

if _test:
    facebook_creds = FacebookCredentials('credentials_test.json')
else:
    facebook_creds = FacebookCredentials('credentials.json')

app.config['OAUTH_CREDENTIALS'] = {
    'facebook': {
        'id': facebook_creds.id,
        'secret': facebook_creds.secret,
    },
}

# Use RDS database if on deployed environment
if 'RDS_DB_NAME' in os.environ:
    db_name = os.environ['RDS_DB_NAME']
    username = os.environ['RDS_USERNAME']
    password = os.environ['RDS_PASSWORD']
    hostname = os.environ['RDS_HOSTNAME']
    port = os.environ['RDS_PORT']
    connection_string = ('mysql://' + username + ':' + password + '@' + hostname + '/' + db_name)
    app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
    site_url = "https://yellowpapersun.com/doge"
else:
    username = 'root'
    hostname = 'localhost'
    db_name = 'dogemo'
    connection_string = ('mysql://' + username + '@' + hostname + '/' + db_name)
    app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
    site_url = "http://localhost:8080" if not ssl else "https://localhost:8443"

db = SQLAlchemy(app)

############
# KVSession
############
from simplekv.db.sql import SQLAlchemyStore
from flask.ext.kvsession import KVSessionExtension
store = SQLAlchemyStore(db.engine, db.metadata, 'sessions')
kvsession = KVSessionExtension(store, app)
