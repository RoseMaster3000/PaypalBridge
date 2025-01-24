from functools import wraps
from flask import session
from PaypalBridge.database.tinydb import fetch_user
import os

# must be logged in (session["username"])
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return {"status":401, "message":'authentication required'}
        kwargs["user"] = fetch_user(session["username"])
        return f(*args, **kwargs)
    return wrapper

# must be temp user (session["username"] and NO email)
def temp_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return {"status":401, "message":'authentication required'}
        kwargs["user"] = fetch_user(session["username"])
        if kwargs["user"]["email"] != None:
            return {"status":401, "message":'temp account required'}
        else:
            return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return {"status":401, "message":'authentication required'}
            
        platform = os.environ.get("platform",None)
        kwargs["user"] = fetch_user(session["username"])
        
        if session["username"] == "admin":
            return f(*args, **kwargs)
        elif platform == "replit":
            return f(*args, **kwargs)
        else:
            return  {"status":403, "message":'admin required', "platform":platform}
        
    return wrapper



def anon_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" in session:
            return {"status":401, "message":'anonymity required'}
        return f(*args, **kwargs)
    return wrapper
