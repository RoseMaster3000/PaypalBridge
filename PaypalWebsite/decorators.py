from functools import wraps
from flask import session, request, after_this_request, redirect
from datetime import datetime
from PaypalWebsite.database.tinydb import fetch_user, log, log_s2s
#from PaypalWebsite.website import app
from PaypalWebsite.isDevelopers import isDeveloper
import os
import time

# prevents cookie from beeing created
'''def no_SessionCookie(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        @after_this_request
        def remove_cookie(response):
            response.delete_cookie('session')
            return response
        return route_func(*args, **kwargs)
    return wrapper'''

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
        user = fetch_user(session.get("username"))
        kwargs["user"] = user

        if user is None or user.get("email") is not None:
            return "temporary account required", 401

        return f(*args, **kwargs)
    return wrapper

# must be registered account (with paypal email)
from flask import jsonify

def email_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print("SESSION USER:", session.get("username"))
        print("LOCAL DECORATOR USED")

        user = fetch_user(session.get("username"))
        kwargs["user"] = user

        if user is None or user.get("email") is None:
            return "You are using a temporary account! Please register with your PayPal email address and then try again.", 401

        return f(*args, **kwargs)
    return wrapper


# must be admin user OR running on development server
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username = session.get("username")
        if not username:
            return redirect("/Login")

        user = fetch_user(username)
        if not user:
            return redirect("/Login")

        kwargs["user"] = user

        if isDeveloper(user["username"], False):
            return f(*args, **kwargs)

        return redirect("/Login")
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

# record this request in the tinydb.jason database
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

# record this request in the s2slogsdb.jason database
def s2slog_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        log_s2s(
            url = request.url,
            path = request.path,
            time = str(datetime.now()),
            created_at=int(time.time()),
            unity = (request.remote_addr in UNITY_IPS),
            ip = request.remote_addr,
            username=session.get("username")
        )
        return f(*args, **kwargs)
    return wrapper