"""Stores the users for the app"""
from login_form import User

users = {}
default_username = "username"
default_user = User("social_id", default_username, "fakeemail", "testaddress")
passwords_to_user = {"pass": default_user}


def save_user(user, password):
    users[user.uid] = user
    passwords_to_user[password] = user
