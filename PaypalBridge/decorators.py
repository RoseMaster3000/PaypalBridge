from functools import wraps
from flask import session
from PaypalBridge.database.tinydb import fetch_user
from PaypalBridge.website import app
import os

# any temp account
def none_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        kwargs["user"] = fetch_user(session["username"])
        return f(*args, **kwargs)
    return wrapper


# must be temp user (session["username"] and NO email)
def temp_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        kwargs["user"] = fetch_user(session["username"])
        
        if kwargs["user"]["email"] != None:
            return {"status":401, "message":'temporary account required'}
        else:
            return f(*args, **kwargs)
    return wrapper

# must be registered account (with paypal email)
def email_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        kwargs["user"] = fetch_user(session["username"])

        if kwargs["user"]["email"] == None:
            return {"status":401, "message": "You are using a temporary account! Please register with your PayPal email address and then try again."}
        else:
            return f(*args, **kwargs)
    return wrapper


# must be admin user OR running on development server
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        platform = os.environ.get("platform",None)
        kwargs["user"] = fetch_user(session["username"])
        
        if kwargs["user"]["username"] == "admin":
            return f(*args, **kwargs)
        elif app.debug == True: # development mode
            return f(*args, **kwargs)
        else:
            return  {"status":403, "message":'admin required'}
    return wrapper
