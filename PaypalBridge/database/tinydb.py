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
    backfix_ads()
    backfix_users()
    purge_request_log()

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


# increment total cashout of user
def increment_cashout(user, increment):
    user = users.get(doc_id=user.doc_id)
    new_total = user.get('total_cashout', 0) + increment
    users.update(
        {'total_cashout': new_total},
        doc_ids=[user.doc_id]
    )


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
def update_user(old_username, **kwargs):
    User = Query()
    user = users.get(User.username == old_username)
    try:
        users.update(kwargs, User.username == old_username)
        return True
    except Exception as e:
        return False

def update_ad(ad, **kwargs):
    ads.update(
        kwargs,
        doc_ids=[ad.doc_id]
    )

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
    # verify userID
    if "userID" not in kwargs:
        raise Exception("Ad logs must have [userID]")
    # sanitize userID  
    if type(kwargs["userID"]) == str and kwargs["userID"].isdigit():
        kwargs["userID"] = int(kwargs["userID"])
    # validate userID
    if type(kwargs["userID"]) != int:
        raise Exception("Ad log [userID] must be integer")
    ads.insert(kwargs)


# get all ads (for specific user)
def fetch_ads(userID=None, redeemed=None):
    if userID:
        Ad = Query()
        if redeemed == None:
            return ads.search(Ad.userID == userID)
        else:
            return ads.search((Ad.userID == userID) & (Ad.redeemed==redeemed))
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


# populate ad type to legacy ads
# "oid": "f88b...",
# "userID": 6,
# "adUnitID": "Fake_Rewarded_Ad",
# "redeemed": false
def backfix_ads():
    for ad in ads.all():
        updates = {}
        if "userID" not in ad:
            continue
        if "redeemed" not in ad:
            updates['redeemed'] = False;
        
        if "adUnitID" not in ad:
            updates['adUnitID'] = "Old_Rewarded_Ad"
            updates['type'] = "Rewarded"
        elif "type" not in ad:
            updates['type'] = "Rewarded" if "Rewarded" in ad["adUnitID"] else "Interstitial"
        elif type(ad['type']) == list:
            updates['type'] = ad['type'][0]

        if updates != {}:
            ads.update(
                updates,
                doc_ids=[ad.doc_id]
            )
            print("updated", ad.doc_id)  


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