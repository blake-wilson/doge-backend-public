from wtforms import Form, TextField, PasswordField, validators
from flask_login.mixins import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "Users"

    def __init__(self, social_id, nickname, email, address):
        self.username = ""
        self.firstname = ""
        self.lastname = ""

        self.social_id = social_id
        self.nickname = nickname
        self.email = email
        self.doge_address = address

    def get_id(self):
        return self.social_id

    # OAuth fields
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    nickname = db.Column(db.String(64), nullable=True)
    email = db.Column(db.String(64), nullable=True)

    doge_address = db.Column(db.String(64), nullable=True)
    # Address user will use to store their own dogecoins external to dogeback
    transfer_address = db.Column(db.String(64), nullable=True)

    def __repr__(self):
        return '<User %r %r %r %r>' % (self.social_id, self.nickname, self.email, self.doge_address)

    def dict(self):
        return {'nickname': self.nickname, 'email': self.email,
                'doge_address': self.doge_address, 'social_id': self.social_id,
                'tranfer_address': self.transfer_address}


class LoginForm(Form):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        # user = User.query.filter_by(
        #     username=self.username.data).first()
        # if user is None:
        #     self.username.errors.append('Unknown username')
        #     return False

        # if not user.check_password(self.password.data):
        #     self.password.errors.append('Invalid password')
        #     return False

        # self.user = user
        return True

    def validate_on_submit(self):
        return True
