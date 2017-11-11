from block_io import BlockIo
from block_io import BlockIoAPIError
import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy import DateTime

from app import db
from blockio_credentials import BlockIOCredentials
from login_form import User
from save_transaction import save_transaction


version = 2  # API version

# DOGE Network
blockio_creds = BlockIOCredentials('credentials_blockio.json')
block_io = BlockIo(blockio_creds.api_key, blockio_creds.secret_pin, version)

class Transaction(db.Model):
    __tablename__ = "Transactions"

    def __init__(self, sender_id, receiver_id, from_addr, to_addr, amount, note):
        self.from_address = from_addr
        self.to_address = to_addr
        self.amount = amount
        self.guid = uuid.uuid4()
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.note = note

        # Fields populated by retrieving user info with sender/receiver ID's
        self.sender = ""
        self.receiver = ""
    from_address = db.Column(db.String(64))
    to_address = db.Column(db.String(64))
    amount = db.Column(db.Numeric(10, 2))
    guid = db.Column(db.String(64), primary_key=True)
    sender_id = db.Column(db.String(64))
    receiver_id = db.Column(db.String(64))
    note = db.Column(db.Text())
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)

    # placeholder for likes on this transaction
    likes = []

    def dict(self):
        return {'id': self.guid, 'sender': self.sender, 'receiver': self.receiver,
                'from_address': self.from_address,
                'to_address': self.to_address, 'amount': self.amount,
                'note': self.note, 'likes': self.likes, 'timestamp': self.timestamp.isoformat()}


class Like(db.Model):
    __tablename__ = "Likes"

    def __init__(self, user_id, transaction_id):
        self.user_id = user_id
        self.transaction_id = transaction_id
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("Users.social_id"), nullable=False)
    transaction_id = db.Column(db.ForeignKey("Transactions.guid"), nullable=False)
    user = db.relationship('User', foreign_keys=user_id)
    transaction = db.relationship('Transaction', foreign_keys=transaction_id)
    __table_args__ = (UniqueConstraint('user_id', 'transaction_id'), )

    def dict(self):
        return {'user_id': self.user_id}



def get_addr():
    """Get a new address"""
    block_io.get_new_address(label='shibe1')


def get_balance(address):
    """Gets the balance of the given address"""

    """Sample Block.IO API response:
    {
      "status" : "success",
      "data" : {
        "network" : "DOGE",
        "available_balance" : "0.00000000",
        "pending_received_balance" : "0.00000000",
        "balances" : [
          {
            "user_id" : 8,
            "label" : "came35",
            "address" : "A25zy2ZqsmftB13Qo5G2V2HPyiVkgPm7Mh",
            "available_balance" : "0.00000000",
            "pending_received_balance" : "0.00000000"
          }
        ]
      }
    }
    """
    try:
        return block_io.get_address_balance(addresses=address)
    except BlockIoAPIError:
        # Address not found
        return None


def system_send_doge(from_addr, to_addr, amount):
    """Sends Doge from the from_addr to the to_addr without creating a Transaction. This can be used
    for system initiated transfers (such as the application of a promo code)"""
    try:
        nonce_id = str(uuid.uuid4()).replace("-", "")
        resp = block_io.withdraw_from_addresses(amounts=str(amount), from_addresses=from_addr,
                                                to_addresses=to_addr, nonce=nonce_id)
        if resp["status"] == "success":
            # Sending Doge was successful
            # TODO: respond with the amount of data sent and the balance of the wallets
            # Sample Block.IO response
            # {
            #     "status" : "success",
            #     "data" : {
            #         "network" : "DOGE",
            #         "txid" : "c96f73f51164b0f56a67201602ddcffb6955c78cf333f6b8c1276cb9de3c99e3",
            #         "amount_withdrawn" : "14.00000000",
            #         "amount_sent" : "12.00000000",
            #         "network_fee" : "2.00000000",
            #         "blockio_fee" : "0.00000000"
            #     }
            # }
            return {"status": "success", "amount_sent": resp["data"]["amount_sent"]}
        elif resp["status"] == "fail":
            return {"status": "failed", "reason": resp["data"]["error_message"]}
    except:
        return {"status": "failed", "reason": "system error communicating with Block.IO"}


def send_doge(sender_id, receiver_id, from_addr, to_addr, amount, note):
    """Sends the specified amount of doge from the "from" address to the "to" address
    Returns the transaction created by sending the doge
    """
    resp = system_send_doge(from_addr, to_addr, amount)
    if resp["status"] != "success":
        # Sending Doge failed, do not write a transaction to DB.
        return None
    return Transaction(sender_id, receiver_id, from_addr, to_addr, amount, note)
