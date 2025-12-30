# https://tinydb.readthedocs.io/en/latest/
from tinydb import TinyDB, Query
from tinydb.table import Document
from random import randint
from uuid import uuid4
#from PaypalWebsite.database import db
import os
import time
from datetime import datetime
import json
from PaypalWebsite.ecpm import get_recent_ecpm

def convert_epoch(epoch_time):
    if type(epoch_time)==str: return epoch_time
    datetime_object = datetime.fromtimestamp(int(epoch_time))
    return datetime_object.strftime("%m/%d/%Y %H:%M:%S")  # Customize the format as needed

#-------FOR oaypal.py 2 defs-----------
# create table "paypal_config" to store mode
# PayPal mode config (sandbox or live)
def set_paypal_mode(mode):
    config_table = db.table('paypal_config')
    config_table.upsert({'mode': mode}, Query().mode.exists())

def get_paypal_mode():
    config_table = db.table('paypal_config')
    result = config_table.get(Query().mode.exists())
    return result['mode'] if result else 'sandbox'
# end of new add if not delete lines 11-22

#---------FOR blueprint_UnityCashoutButton.py 4 defs-------------
#create table "cashout_override" to store mode
def set_override_status(enabled: bool):
    db.table('cashout_override').upsert({'enabled': enabled}, Query().enabled.exists())

def get_override_status():
    result = db.table('cashout_override').get(Query().enabled.exists())
    return result['enabled'] if result else False

def set_interactable_status(enabled: bool):
    db.table('cashout_interactable').upsert(
        {'enabled': enabled},
        Query().enabled.exists()
    )

def get_interactable_status():
    result = db.table('cashout_interactable').get(Query().enabled.exists())
    return result['enabled'] if result else True   # default = True
#---------END of blueprint_UnityCashoutButton.py-------------


# generate current epoch time INT (seconds since January 1, 1970)
def now():
    return int(time.time())

# initialize database
def initialize_db(app):
    global db, users, ads, REVENUE_FILE
    REVENUE_FILE = os.path.join(app.config['DATABASE_FOLDER'], "revenue.json")
    dbPath = os.path.join(app.config['DATABASE_FOLDER'], 'tinydb.json')
    print("TinyDB is using:", dbPath)
    db = TinyDB(dbPath)
    users = db.table('users')
    backfix_users()
    purge_request_log()
    delete_old_tables()
    create_admin()

# Create admin account (if missing)
def create_admin():
    if fetch_user("admin") != None: return
    hashedPass = b'$2b$12$6Fjtz.GaNQlHwA1vOGCjP.pQeHWEiAij7T.4X3vR83/QN1S.Wg3u6'
    newUser = create_user(
        username = "admin",
        email = "sb-obcg635472172@personal.example.com",
        password = hashedPass.decode('utf-8'),
        gems = 0,
        bonus = 0,
        rewarded = 0,
        interstitial = 0,
        total_cashout = 0,
        children = [],
        earnings = 0,
        cashouts = [],
        created_at = time.time()
    )
    print("admin has been generated!")


# old tables from early in development
def delete_old_tables():
    db.drop_table('s2s')
    db.drop_table('ads')

# get one user
def fetch_user(username):
    User = Query()
    
    # If username is already a Document, return it
    if isinstance(username, Document):
        return username
    
    # If username is a doc_id (int)
    if isinstance(username, int):
        return users.get(doc_id=username)
    
    # If username is a string
    if isinstance(username, str):
        return users.get(User.username == username)
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



# Record cashout in database
def log_cashout(username, gemCount, TotalPayout, EntitledPayout, AdminPayout): 
    

    # increment total cashout of user
    user = fetch_user(username)
    user['total_cashout'] = user.get('total_cashout', 0) + EntitledPayout
    user['earnings'] -= TotalPayout
    user['cashouts'].append({
        "gems": gemCount,
        "TotalPayout": TotalPayout,  # how much send via paypal (before paypal fees)
        "UserPayout": EntitledPayout,# how much recv by user (after paypal fee)
        "AdminPayout": AdminPayout,  # cut left behind for Admin (before paypal fees)
        "AdminCollected": False,     # [T/F] has the Admin collected their cut?
        "time": now()
    })
    
    try:
        users.update({
            "total_cashout": user["total_cashout"],
            "earnings": user["earnings"],
            "cashouts": user["cashouts"]
        }, doc_ids=[user.doc_id])


        return True, user
    except Exception as e:
        print("LOG CASHOUT ERROR:", e)
        return False, user


def increment_revenue_all(increment):
    cash_data = fetch_revenue()
    cash_data["gross"] += increment
    cash_data["player"] += increment * 0.70
    cash_data["website"] += increment * 0.30
    with open(REVENUE_FILE, 'w') as file:
        json.dump(cash_data, file, indent=4)

# increase admin cash running total for a specific key
def increment_revenue(key, increment):
    cash_data = fetch_revenue()
    if key in cash_data:
        cash_data[key] += increment
    else:
        cash_data[key] = increment
    with open(REVENUE_FILE, 'w') as file:
        json.dump(cash_data, file, indent=4)

# get current admin cash value for a specified key
def fetch_revenue(key=None):
    if not os.path.isfile(REVENUE_FILE):
        reset_revenue()
    with open(REVENUE_FILE, 'r') as file:
        try:
            data = json.load(file)
            if key:
                return data.get(key, 0)
            else:
                return data
        except json.JSONDecodeError:
            print("Error decoding JSON. Resetting admin cash.")
            reset_revenue()
            return fetch_revenue(key) # Retry fetching after reset

# reset admin cash file (set specified keys to 0)
def reset_revenue():
    cash_data = {
        "gross": 0,
        "website": 0,
        "player": 0
    }
    with open(REVENUE_FILE, 'w') as file:
        json.dump(cash_data, file, indent=4)

# set admin cash value to specific value
def set_revenue(key, value=0):
    cash_data = fetch_revenue()
    print(f"Current cash data: {cash_data}")
    if key in cash_data:
        cash_data[key] = value
    else:
        cash_data[key] = value
    print(f"Updated cash data: {cash_data}")
    with open(REVENUE_FILE, 'w') as file:
        json.dump(cash_data, file, indent=4)


# delete temp uses (eg 5: accounts older than [5] days old)
def purge_users(dayRange=0):
    cutoffDate = now() - (dayRange*886400)
    User = Query()
    removed_users = users.remove(
        (User.email == None) & 
        (User.created_at < cutoffDate) &
        (User.gems == 0) &
        (User.bonus == 0)
    )
    return len(removed_users)


# Delete all records that are not S2S related
def purge_request_log():
    requests_table = db.table('Requests')
    Record = Query()
    requests_table.remove(~ (Record.path.one_of(["/S2S", "/S3S"])))


# Update the user record
def update_user(old_username, new_username=None, **kwargs):
    User = Query()
    user = users.get(User.username == old_username)

    if not user:
        print(f"UPDATE USER ERROR: user '{old_username}' not found")
        return False

    print(f"UPDATE USER FOUND: doc_id={user.doc_id}, current={user}")

    # Build update fields
    update_fields = kwargs.copy()

    # If renaming user, include new username
    if new_username is not None:
        update_fields["username"] = new_username

    print(f"UPDATE USER FIELDS: {update_fields}")

    try:
        users.update(update_fields, doc_ids=[user.doc_id])
        updated = users.get(doc_id=user.doc_id)
        print(f"UPDATE USER SUCCESS: updated={updated}")
        return True

    except Exception as e:
        print("UPDATE USER ERROR:", e)
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
        gems = parent["gems"] + child["gems"],
        bonus = parent["bonus"] + child["bonus"]
    )

    # mark child ad owned by parent
    # empty child's gems
    update_user(
        child["username"],
        parent = parent.doc_id,
        gems = 0,
        bonus = 0
    )


# log 1 interstitial ad
def record_rewarded(user, count=1):
    user = fetch_user(user)
    rewarded_ecpm = get_recent_ecpm("rewarded")
    # increment ad count & earnings
    user['rewarded'] += count
    generated_revenue = rewarded_ecpm / 1000 * count
    user['earnings'] += generated_revenue
    # update database
    users.update({
        "rewarded": user["rewarded"],
        "earnings": user["earnings"]
    }, doc_ids=[user.doc_id])
    # track our profits
    print(generated_revenue* 0.30)
    increment_revenue_all(generated_revenue)


# log 1 rewarded ad
def record_interstitial(user, count=1):
    user = fetch_user(user)
    interstitial_ecpm = get_recent_ecpm("interstitial")
    # increment ad count & earnings
    user['interstitial'] += count
    generated_revenue = interstitial_ecpm / 1000 * count
    user['earnings'] += generated_revenue
    # update database
    users.update({
        "interstitial": user["interstitial"],
        "earnings": user["earnings"]
    }, doc_ids=[user.doc_id])
    # track out profits
    increment_revenue_all(generated_revenue)

# log rewarded+interstitial ad(s) in database 
def record_ad_round(user, count=1):
    user = fetch_user(user)
    interstitial_ecpm = get_recent_ecpm("interstitial")
    rewarded_ecpm = get_recent_ecpm("rewarded")
    user['interstitial'] += count
    user['rewarded'] += count
    interstitial_revenue = interstitial_ecpm / 1000 * count
    user['earnings'] += interstitial_revenue
    rewarded_revenue = rewarded_ecpm / 1000 * count
    user['earnings'] += rewarded_revenue
    user['gems'] += 55 * count
    # update database
    users.update({
        "interstitial": user["interstitial"],
        "rewarded": user["rewarded"],
        "earnings": user["earnings"],
        "gems": user["gems"]
    }, doc_ids=[user.doc_id])

    increment_revenue_all((interstitial_revenue+rewarded_revenue))


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
        if "cashouts" not in user:
            users.update(
                {'cashouts': []},
                doc_ids=[user.doc_id]
            ) 
        if "earnings" not in user:
            users.update(
                {'earnings': 0.00000},
                doc_ids=[user.doc_id]
            ) 