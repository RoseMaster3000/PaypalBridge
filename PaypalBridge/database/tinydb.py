# https://tinydb.readthedocs.io/en/latest/

# initialize database
from tinydb import TinyDB, Query
import os

# initialize database
def initialize_db(path):
    dbPath = os.path.join(path, '..', 'DatabaseStorage', 'users.tinydb.json')
    global users
    users = TinyDB(dbPath)

# get one user
def fetch_user(username):
    User = Query()
    result = users.search(User.username == username)
    if len(result) == 0:
        return None
    else:
        return result[0]

# get all users
def fetch_users():
    return users.all()

# create new user
def create_user(**kwargs):
    if "username" not in kwargs:
        raise Exception("USER must have a username")
    if fetch_user(kwargs["username"]) != None:
        return None
    doc_id = users.insert(kwargs)
    return users.get(doc_id=doc_id)

# Update the user record
def update_user(old_username, **kwargs):
    User = Query()
    user = users.get(User.username == old_username)
    try:
        users.update(kwargs, User.username == old_username)
        return True
    except Exception as e:
        return False

# **delete a user record**
def delete_user(username):
    User = Query()
    try:
        users.remove(User.username == username)
        return True
    except Exception as e:
        return False