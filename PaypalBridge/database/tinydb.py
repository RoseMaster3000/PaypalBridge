# https://tinydb.readthedocs.io/en/latest/
from tinydb import TinyDB, Query
from random import randint
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
    ads = db.table('ads')
    db.drop_table('s2s')



# get one user
def fetch_user(username):
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


# delete temp uses (eg 5: accounts older than [5] days old)
def purge_users(dayRange=0):
    cutoffDate = now() - (dayRange*886400)
    User = Query()
    removed_users = users.remove(
        (User.email == None) & 
        (User.created_at < cutoffDate)
    )
    return len(removed_users)


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


# log ad in database 
def record_ad(**kwargs):
    if "sid" not in kwargs:
        raise Exception("Ad logs must have [sid]")
    if not kwargs["sid"].isdigit():
        raise Exception("Ad log [sid] must be integer")
    else:
        kwargs["sid"] = int(kwargs["sid"])
    ads.insert(kwargs)


# get all ads (for specific user)
def fetch_ads(userID=None, redeemed=None):
    if userID:
        Ad = Query()
        if redeemed == None:
            return ads.search(Ad.sid == userID)
        else:
            return ads.search((Ad.sid == userID) & (Ad.redeemed==redeemed))
    else:
        return ads.all()



def fetch_all(tableName):
    table = db.table(tableName)
    return table.all()


# insert data into specified table
def log(tableName, **kwargs):
    kwargs['created_at'] = now()
    table = db.table(tableName)
    table.insert(kwargs)




# add random dates to old users (random time within last [dayRange] days)
def datify_users(dayRange=10):
    for user in users.all():
        if 'created_at' not in user:
            random_time = now() - randint(0, dayRange*886400)
            users.update(
                {'created_at': random_time},
                doc_ids=[user.doc_id]
            )
            print("updated", user.doc_id)