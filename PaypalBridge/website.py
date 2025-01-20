from flask import Flask, render_template, request, redirect, session, jsonify
from flask_bcrypt import Bcrypt
from PaypalBridge.paypal import send_money
from PaypalBridge.database.tinydb import *
from PaypalBridge.decorators import login_required, anon_required, temp_required
from uuid import uuid4
import os

# initialize modules
app = Flask(__name__)
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
bcrypt = Bcrypt(app)
initialize_db(app.root_path)

@app.before_request 
def verify_auth():
    session["replit"] = (os.environ.get("platform",None) == "replit")
    if "username" not in session:
        generate_temp_user()


def generate_temp_user():
    user = create_user(
        username = str(uuid4()),
        email = None,
        password = str(uuid4()),
        gems = 0
    )
    session["username"] = user["username"]
    session["gems"] = user["gems"]
    
@app.route("/TempUser", methods=['POST'])
def temp_user():
    generate_temp_user()
    return "Temp User Generated<a href='/'>Go Back<a>"


# ask server for username
@app.route("/Identity", methods=['POST'])
def identity():
    return session.get("username", "[None]")


# ask server for SID (document ID)
@app.route("/SID")
@login_required
def SID(user):
    return str(user.doc_id)


# debugger view (veiw/create users)
@app.route('/')
@login_required
def index(user):
    # get all users
    users = fetch_users()
    # display page
    return render_template('index.html', users=users, user=user)


# 5 gems / 1 ad (5/1000)

# Create a new account
@app.route('/CreateUser', methods=['POST'])
@login_required
def CreateUser(user):
    # validate form
    if "" in request.form.values():
        return "Error: Please Fill All Fields!"
        
    # validate username (length)
    if len(request.form['username']) >= 36:
        return "Error: Username too long"

    # inherit gems from previous (temp) account
    if user["email"] == None:
        inheritedGems = user["gems"]
        delete_user(user["username"])       # (old) temp account
    else:
        inheritedGems = 0
    
    # store new user in database
    newUser = create_user(
        username = request.form['username'],
        email = request.form['email'],
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8'),
        gems = inheritedGems
    )
    if user==None:
        return "Could not create user"

    # log user in  
    session["username"] = request.form['username']
    session["gems"] = newUser["gems"]
    return f"User has been created!<br><a href='/'>Go Back<a>"


# Increment Gems
@app.route('/GetGem', methods=['POST'])
@login_required
def GetGem(user):
    user["gems"] += 1
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


def CalculatePayout(gemCount):
    SingleAdRevenue = 5 / 1000
    SingleGemRevenue = SingleAdRevenue / 5
    RevShare = 0.20
    TotalCut = gemCount * (SingleGemRevenue * RevShare)
    PaypalProcessingFee = (TotalCut * 0.029) + 0.30
    EntitledCut = TotalCut - PaypalProcessingFee
    TotalCut = int(TotalCut*100)/100
    EntitledCut = int(EntitledCut*100)/100
    return TotalCut, EntitledCut


def CalculateMinimumGems():
    EntitledPayout = 0
    gems = 0
    while EntitledPayout < 0.01:
        gems += 1
        TotalPayout, EntitledPayout = CalculatePayout(gems)
    return gems
GEM_MINIMUM = CalculateMinimumGems()


# Cashout Gems
@app.route('/Cashout', methods=['POST'])
@login_required
def Cashout(user):
    # validate inputs
    try:
        email = user["email"]
        gemCount = int(request.form["gems"])
    except:
        return "Invalid Gem Count"
    
    # make sure NOT temp user
    if user["email"] == None:
        return "You are using a temporary account! Please register with your PayPal email address and then try to cashout again."
        
    # verify gem count
    if (user["gems"] < gemCount):
        return "You requested more gems than you have!"
    if gemCount < GEM_MINIMUM:
        return f"Processing fees outweigh your cashout ({GEM_MINIMUM} gems required)"
        
    # verify (unredeemed) ads have been watched (5 gems: 1 ad)

    # mark ads as redeemed / decrement gems
    

    # generate paypal cashout
    TotalPayout, EntitledPayout = CalculatePayout(gemCount)
    send_paypal_money(user["email"], TotalPayout)

    return f"Cashout of ${EntitledPayout:0.2f} sucessfully send to {email}"

# Increment Gems
@app.route('/GemCount')
@login_required
def GemCount(user):
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# TESTING PURPOSES ONLY
@app.route('/get_gem')
@login_required
def get_gem(user):
    if session["replit"]:
        user["gems"] += 1
        update_user(user["username"], **user)
        session["gems"] = user["gems"]
        return redirect("/")
    else:
        return "This route only workes on REPLIT server."


# UNITY will tell us when ads have been watched by users
# https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks
@app.route('/S2S', methods=['POST'])
@login_required
def WatchAd(user):
    log_ad(
        userID = user.doc_id,
        adUnitId = request.form['adUnitId'],
        redeemed = False
    )
    return "Ad has been logged<br><a href='/'>Go Back<a>"

@app.route('/SeeAds')
@login_required
def SeeAds(user):
    if session["replit"]:
        return jsonify(fetch_ads(user.doc_id))
    else:
        return 403, "Permission Denied"


# take over temp_user account (fake "registration")
@app.route('/Login', methods=['POST'])
@login_required
def login(user):    
    newUser = fetch_user(request.form['username'])

    # verify user
    if newUser==None:
        return f"User Does not Exist<br><a href='/'>Go Back<a>"
    
    # verify password
    if not bcrypt.check_password_hash(newUser['password'], request.form['password']):
        return f"Password is Incorrect<br><a href='/'>Go Back<a>"

    # inherit gems from previous (temp) account
    if "email" in user and user["email"] == None:
        newUser["gems"] += user["gems"]
        update_user(newUser["username"], **newUser) # real account
        delete_user(user["username"])       # (old) temp account
    
    # log user in  
    session["username"] = newUser["username"]
    session["gems"] = newUser["gems"]
    return f"Logged in sucessful<br><a href='/'>Go Back<a>"


# delete multiple users 
@app.route('/DeleteUsers', methods=['POST'])
def delete_users():
    usernames = request.form.getlist('usernames') 
    for username in usernames: 
        session_check(username)
        delete_user(username) 
    return redirect('/')


# **New route to delete a user**
@app.route('/DeleteUser', methods=['POST'])
def delete_user_route():
    username = request.form['username']
    delete_user(username)
    session_check(username)
    return f"User [{username}] has been deleted<br><a href='/'>Go Back<a>"


# if you delete yourself, revoke the session 
def session_check(username):
    if "username" in session:
        if session["username"] == username:
            del session["username"]
            return

@app.route('/Logout', methods=['POST'])
def logout():
    session.pop("username", None)
    return f"You are logged out<br><a href='/'>Go Back<a>"


if __name__ == '__main__':
    app.run(debug=True)
