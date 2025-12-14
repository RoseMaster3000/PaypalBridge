from functools import wraps
from flask import session, request, after_this_request
from datetime import datetime
from PaypalWebsite.database.tinydb import fetch_user, log
from PaypalWebsite.website import app, isDeveloper
import os

# prevents cookie from beeing created
def no_SessionCookie(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        @after_this_request
        def remove_cookie(response):
            response.delete_cookie('session')
            return response
        return route_func(*args, **kwargs)
    return wrapper

# any temp account
def none_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username = session.get("username")
        user = fetch_user(username) if username else None
        kwargs["user"] = user
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
        kwargs["user"] = fetch_user(session["username"])
        if isDeveloper():
            return f(*args, **kwargs)
        else:
            return  {"status":403, "message":'admin required'}
    return wrapper


# IP addresses for Unity S2S servers (are these real?...)
UNITY_IPS = [
    "185.33.96.0",
    "185.98.36.0",
    "35.235.16.8",
    "35.227.129.136",
    "35.234.176.136",
    "35.192.193.0",
    "35.205.0.8"
]

# record this request in the database
def log_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        log(
            "Requests",
            url = request.url,
            path = request.path,
            time = str(datetime.now()),
            unity = (request.remote_addr in UNITY_IPS),
            ip = request.remote_addr
        )
        return f(*args, **kwargs)
    return wrapper