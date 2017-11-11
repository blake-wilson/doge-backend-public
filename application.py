import decimal
import base64
import json
import logging
import os
from io import BytesIO
from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from flask import current_app
from flask_cors import cross_origin
from flask_login import LoginManager
from login_form import LoginForm
from flask_login import login_required
from flask_login import current_user
from flask_login import login_user
from flask_login import logout_user
from transaction import get_balance
from transaction import send_doge
from transaction import system_send_doge
from login_form import User
from transaction import Transaction
from transaction import Like
from transaction import block_io
from load_transactions import load_transactions_for_user
from oauth_signin import OAuthSignIn
from flask_sqlalchemy import SQLAlchemy
from rauth import OAuth2Session
from app import app as application
from app import db
from app import site_url
from urllib.request import unquote
from PIL import Image
import zbarlight
from addresses import addresses
from errors import errors


login_manager = LoginManager()

test_user = User("social_id", "blake", "email@fake.com", "9xNVw9mWznyWqCj6crqBWHBku3V3vsSras")
test_user.firstname = "Blake"
test_user.lastname = "Wilson"
test_user.doge_address = "9xNVw9mWznyWqCj6crqBWHBku3V3vsSras"
# user.address = "2NFEu8FyS3BTkv4ZD9HihBdsX5f4G2fHGK8u"
test_user.id = ""

other_test_user = User("social_id", "blake", "email@fake.com", "testaddress")
other_test_user.id = "other"
other_test_user.doge_address = "testaddress"

application.secret_key = "some secret key"


@application.before_first_request
def create_tables():
    db.create_all()

# initialize login manager
login_manager.init_app(application)


def obj_dict(obj):
    return obj.__dict__


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, Like):
        return obj.dict()
    if isinstance(obj, User):
        return obj.dict()
    raise TypeError("obj %r is not JSON serializable" % obj)


@application.route("/")
@login_required
@cross_origin(supports_credentials=True)
def root():
    return "OK"


@login_manager.request_loader
def request_loader(request):
    # TODO: Do not use Basic Auth
    # login user with basic auth. Format: ```Basic Base64EncodedUsername:Base64EncodedPassword
    auth = request.headers.get('Authorization')
    if auth:
        auth = auth.replace('Basic ', '', 1)
        try:
            auth = base64.b64decode(auth)
        except TypeError:
            pass
        split = auth.decode("utf-8").split(":")
        # _user = get_user(split[0], split[1])
        # TODO: do not use this method to get social ID
        _user = User.query.filter_by(social_id=split[0]).first()
        if _user:
            return _user
    # Could not login user
    return None


@application.route("/searchusers/<user_hint>")
@login_required
@cross_origin(supports_credentials=True)
def load_users(user_hint):
    """Load users using the provided text as a hint"""
    q = User.query.filter(User.nickname.like(user_hint + '%'))
    users = q.all()
    return json.dumps(users, default=decimal_default)


@application.route("/balance", methods=['GET'])
@login_required
@cross_origin(supports_credentials=True)
def get_user_balance():
    """Gets the balance for the logged in user"""
    balance = get_balance(current_user.doge_address)
    if balance is None:
        return "Wallet not found"
    return jsonify(balance)


@application.route("/load_transactions_for_friends")
@login_required
@cross_origin(supports_credentials=True)
def load_user_transactions_for_friends():
    """Gets all transactions for the logged in user and their friends"""
    fs = get_friends()
    if fs is None:
        return redirect(url_for('oauth_authorize', provider="facebook", _external=True))
    search_ids = ['facebook$' + f['id'] for f in fs]
    search_ids.append(current_user.social_id)

    start_time = unquote(request.args.get('start')) if request.args.get('start') is not None else None
    query = Transaction.query.filter((Transaction.sender_id.in_(search_ids)) |
                                     (Transaction.receiver_id.in_(search_ids)))

    if start_time is not None:
        print("Load transactions before " + start_time)
        query = query.filter(Transaction.timestamp < start_time)

    query = query.order_by(Transaction.timestamp.desc())
    limit = unquote(request.args.get('limit')) if request.args.get('limit') is not None else None

    if limit is not None:
        query = query.limit(int(limit))

    transactions = query.all()
    # Dict of sender/receiver user ID
    user_ids = set()
    for t in transactions:
        # Load likes for the transaction
        q = Like.query.filter(Like.transaction_id == t.guid)
        t.likes = q.all()
        user_ids.add(t.receiver_id)
        user_ids.add(t.sender_id)

    # Get the users for each transaction
    result = User.query.filter(User.social_id.in_(list(user_ids))).all()

    # Construct map of user ID to user
    users = {}
    for u in result:
        users[u.social_id] = u

    for t in transactions:
        t.sender = users[t.sender_id].nickname
        t.receiver = users[t.receiver_id].nickname

    return json.dumps([t.dict() for t in transactions], default=decimal_default)


@application.route("/load_transactions")
@login_required
@cross_origin(supports_credentials=True)
def load_user_transactions():
    """Get all transactions for the logged in user (sent or received)"""
    transactions = Transaction.query.filter((Transaction.sender_id == current_user.social_id) |
                                            (Transaction.receiver_id == current_user.social_id)).all()

    # Dict of sender/receiver user ID
    user_ids = set()
    for t in transactions:
        # Load likes for the transaction
        q = Like.query.filter(Like.transaction_id == t.guid)
        t.likes = q.all()
        user_ids.add(t.receiver_id)
        user_ids.add(t.sender_id)

    # Get the users for each transaction
    result = User.query.filter(User.social_id.in_(list(user_ids))).all()

    # Construct map of user ID to user
    users = {}
    for u in result:
        users[u.social_id] = u

    for t in transactions:
        t.sender = users[t.sender_id].nickname
        t.receiver = users[t.receiver_id].nickname

    return json.dumps([t.dict() for t in transactions], default=decimal_default)


@application.route("/send/<receiver_id>/amount/<float:amount>", methods=['POST'])
@login_required
@cross_origin(supports_credentials=True)
def send_user_doge(receiver_id, amount):
    note = request.form["note"]
    # Get user's address for receiver
    receiver = get_user(receiver_id)
    if receiver is None:
        return "User not found", 400

    transaction = send_doge(current_user.social_id, receiver_id,
                            current_user.doge_address, receiver.doge_address, amount, note)
    if transaction is None:
        return "Error sending Doge", 400
    db.session.add(transaction)
    db.session.commit()
    return "OK"


@application.route("/like/<transaction_id>", methods=['POST'])
@login_required
@cross_origin(supports_credentials=True)
def like(transaction_id):
    """Likes the given transaction for the logged in user"""

    try:
        l = Like(current_user.social_id, transaction_id)
        db.session.add(l)
        db.session.commit()
    except:
        return "Invalid", 400

    return "OK"


# @application.after_request
# def after_request(response):
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers', 'Origin,Accept,X-Requested-With,Content-Type,Authorization')
#     response.headers.add('Access-Control-Allow-Methods', 'OPTIONS,GET,PUT,POST,DELETE')
#     return response


def get_user(user_id):
    # return user
    user = User.query.filter_by(social_id=user_id).first()
    return user


@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)


@application.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(site_url + '/login.html')


@application.route('/wallet')
@login_required
@cross_origin(supports_credentials=True)
def get_transfer_address():
    transfer_address = current_user.transfer_address
    return transfer_address


@application.route('/wallet/<address>', methods=['POST'])
@login_required
@cross_origin(supports_credentials=True)
def set_wallet(address):
    """Sets the doge wallet for the logged in user"""
    social_id = current_user.social_id
    user = User.query.filter_by(social_id=social_id).first()
    user.transfer_address = address
    db.session.commit()
    return "OK"


@application.route('/registerwallet', methods=['POST'])
@login_required
@cross_origin(supports_credentials=True)
def register_wallet():
    """Registers the BlockIO address encoded in a QR code provided by the user.
    If the user already has a wallet registered, registration will fail.
    """
    social_id = current_user.social_id
    user = User.query.filter_by(social_id=social_id).first()

    im = Image.open(BytesIO(base64.b64decode(request.data)))
    address = zbarlight.scan_codes('qrcode', im)
    if address is None or len(address) > 1:
        return json.dumps({'status': 'failed', 'code': 1, 'reason': errors[1]})
    address = address[0].decode("utf-8")

    if address not in addresses:
        return json.dumps({'status': 'failed', 'code': 2, 'reason': errors[2]})

    # Get balance and send doge to logged in user if there is any Doge in the wallet
    balance = get_balance(address)
    if balance is None:
        return json.dumps({'status': 'failed', 'code': 3, 'reason': errors[3]})
    available_balance = float(balance["data"]["available_balance"])
    if available_balance < 2:
        return json.dumps({'status': 'failed', 'code': 4, 'reason': errors[4]})

    # Send doge in wallet to current user - leave 2 Doge for network fee
    resp = system_send_doge(address, user.doge_address, available_balance - 2)
    return json.dumps(resp)


@application.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(site_url + '/index.html')
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@application.route('/friends')
@login_required
@cross_origin(supports_credentials=True)
def friends():
    """Gets the friends of the current user"""
    # check to make sure the user authorized the request
    fb_creds = application.config['OAUTH_CREDENTIALS']['facebook']
    oauth = OAuth2Session(fb_creds['id'], fb_creds['secret'], session['access_token'])
    f = oauth.get('https://graph.facebook.com/me/friends').json()

    # TODO: handle paging of users
    users = f['data']

    return json.dumps(users)


def get_friends():
    """Gets the friends of the current user"""
    # check to make sure the user authorized the request
    fb_creds = application.config['OAUTH_CREDENTIALS']['facebook']
    if session.get('access_token') is None:
        return None
    oauth = OAuth2Session(fb_creds['id'], fb_creds['secret'], session['access_token'])
    f = oauth.get('https://graph.facebook.com/me/friends').json()

    # TODO: handle paging of users
    users = f['data']
    return users


@application.route('/transfer/<address>/<float:amount>', methods=['POST'])
@login_required
@cross_origin(supports_credentials=True)
def transfer_funds(address, amount):
    """Sends all doge from the users balance to their transfer address"""
    # Get balance for user's address
    balance = get_balance(current_user.doge_address)
    if balance is None:
        return "Could not retrieve balance from Doge network", 500
    if amount > float(balance["data"]["available_balance"]):
        return "Not enough Doge in wallet to send " + str(amount) + " Doge", 400
    try:
        resp = system_send_doge(current_user.doge_address,
                                address, amount)
    except:
        return "Doge transfer failed", 500
    if resp["status"] == "failed":
        return "Doge transfer failed: " + resp["reason"], 500

    return resp["amount_sent"] + " Doge transferred"


@application.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        # Already logged in
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, nickname = oauth.callback()
    if social_id is None:
        # flash('Authentication failed.')
        logging.warning("Authentication failed")
        return redirect(url_for('index'))

    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        # Create a dogecoin address for the user
        resp = block_io.get_new_address()
        address = resp['data']['address']
        user = User(social_id, nickname, "fake@notarealemail.com", address)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    # return redirect(url_for('index'))
    return redirect(site_url + '/index.html')


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(site_url + '/login.html')


if __name__ == "__main__":
    application.run(threaded=True, debug=True)
