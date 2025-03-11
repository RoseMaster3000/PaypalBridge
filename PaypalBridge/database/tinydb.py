# https://tinydb.readthedocs.io/en/latest/
from tinydb import TinyDB, Query
from tinydb.table import Document
from random import randint
from uuid import uuid4
import os
import time

# generate current time INT (seconds since January 1, 1970)
def now():
    return int(time.time())


# initialize database
def initialize_db(path):
    dbPath = os.path.join(path, '..', 'DatabaseStorage', 'tinydb.json')
    os.makedirs(os.path.dirname(dbPath), exist_ok=True)
    global db, users, ads
    db = TinyDB(dbPath)
    users = db.table('users')
    backfix_users()
    purge_request_log()
    delete_old_tables()


# old tables from early in development
def delete_old_tables():
    db.drop_table('s2s')
    db.drop_table('ads')

# get one user
def fetch_user(username):
    if type(username) == Document:
        return username
    if type(username) == int:
        return users.get(doc_id=username)
    elif type(username) == str:
        User = Query()
        result = users.search(User.username == username)
        if len(result) == 0:
            return None
        else:
            return result[0]
    else:
        return None

# get one user
def fetch_user_email(email):
    User = Query()
    result = users.search(User.email == email)
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
    kwargs["created_at"] = now()
    doc_id = users.insert(kwargs)
    return users.get(doc_id=doc_id)


def record_cashout(user, increment):
    # increment total cashout of user
    user = users.get(doc_id=user.doc_id)
    new_total = user.get('total_cashout', 0) + increment
    users.update(
        {'total_cashout': new_total},
        doc_ids=[user.doc_id]
    )

    # Also log cashout redemption?
    # TODO

    # return updated user
    return True, user

# delete temp uses (eg 5: accounts older than [5] days old)
def purge_users(dayRange=0):
    cutoffDate = now() - (dayRange*886400)
    User = Query()
    removed_users = users.remove(
        (User.email == None) & 
        (User.created_at < cutoffDate)
    )
    return len(removed_users)


# Delete all records that are not S2S related
def purge_request_log():
    requests_table = db.table('Requests')
    Record = Query()
    requests_table.remove(~ (Record.path.one_of(["/S2S", "/S3S"])))


# Update the user record
def update_user(user, **kwargs):
    user = fetch_user(user)
    print(user)
    print(user.doc_id)
    print(kwargs)
    try:
        users.update(kwargs, doc_ids=[user.doc_id])
        return True
    except Exception as e:
        print()
        return False

# **delete a user record**
def delete_user(username):
    User = Query()
    try:
        users.remove(User.username == username)
        return True
    except Exception as e:
        return False

def adopt_user(parent, child):
    # add child to parent's child list
    User = Query()
    users.update(lambda doc:
        doc['children'].append(child.doc_id),
        doc_ids = [parent.doc_id]
    )

    # parent takes all the child's gems 
    update_user(
        parent["username"],
        gems = parent["gems"] + child["gems"]
    )

    # mark child ad owned by parent
    # empty child's gems
    update_user(
        child["username"],
        parent = parent.doc_id,
        gems = 0
    )


# log 1 interstitial ad
def record_rewarded(user, count=1):
    user = fetch_user(user)
    r = user['rewarded'] + count
    users.update(
        {'rewarded': r},
        doc_ids=[user.doc_id]
    )

# log 1 rewarded ad
def record_interstitial(user, count=1):
    print("=======================")
    print(user)
    print(type(user))
    user = fetch_user(user)
    print("=======================")
    print(user)
    i = user['interstitial'] + count
    users.update(
        {'interstitial': i},
        doc_ids=[user.doc_id]
    )

# log rewarded+interstitial ad(s) in database 
def record_ad_round(user, count=1):
    user = fetch_user(user)
    r = user['rewarded'] + count
    i = user['interstitial'] + count
    users.update(
        {'rewarded': r, 'interstitial': i},
        doc_ids=[user.doc_id]
    )

def fetch_all(tableName):
    table = db.table(tableName)
    return table.all()


# insert data into specified table
def log(tableName, **kwargs):
    kwargs['created_at'] = now()
    table = db.table(tableName)
    table.insert(kwargs)


# populate random dates to legacy users (random time within last [dayRange] days)
def backfix_users(dayRange=10):
    for user in users.all():
        if 'created_at' not in user:
            random_time = now() - randint(0, dayRange*886400)
            users.update(
                {'created_at': random_time},
                doc_ids=[user.doc_id]
            )
            print("updated", user.doc_id)
        if 'total_cashout'  not in user:
            users.update(
                {'total_cashout': 0.00},
                doc_ids=[user.doc_id]
            )
            print("updated", user.doc_id)
        if 'children' not in user:
            users.update(
                {'children': []},
                doc_ids=[user.doc_id]
            )
        if 'bonus' not in user:
            users.update(
                {'bonus': 0},
                doc_ids=[user.doc_id]
            )

        if 'rewarded' not in user:
            users.update(
                {'rewarded': 0},
                doc_ids=[user.doc_id]
            ) 
        if 'interstitial' not in user:
            users.update(
                {'interstitial': 0},
                doc_ids=[user.doc_id]
            ) 