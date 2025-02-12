from flask import Flask, render_template, request, redirect, session, jsonify, abort, make_response
from urllib.parse import unquote, urlparse
import hmac
import hashlib
from flask_bcrypt import Bcrypt
from PaypalBridge.paypal import create_payout
from PaypalBridge import SECRET
from PaypalBridge.database.tinydb import *
from PaypalBridge.decorators import *
from datetime import datetime
from uuid import uuid4
import os

# initialize modules
app = Flask(__name__)
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
bcrypt = Bcrypt(app)
initialize_db(app.root_path)


def CreateAdmin():
    hashedPass = b'$2b$12$6Fjtz.GaNQlHwA1vOGCjP.pQeHWEiAij7T.4X3vR83/QN1S.Wg3u6'
    newUser = create_user(
        username = "admin",
        email = "admin@mail.com",
        password = hashedPass.decode('utf-8'),
        gems = 0
    )
    if newUser==None:
        print("Could not create user")

    print("User has been created!")

if __name__=="__main__":
    CreateAdmin()