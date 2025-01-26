from flask import Flask, render_template, request, redirect, session, jsonify, abort
from urllib.parse import unquote, urlparse
import hmac
import hashlib
from flask_bcrypt import Bcrypt
from PaypalBridge.paypal import send_money
from PaypalBridge import SECRET
from PaypalBridge.database.tinydb import *
from PaypalBridge.decorators import *
from datetime import datetime
from uuid import uuid4
import os

# IP addresses fro Unity S2S servers
UNITY_IPS = [
    "185.33.96.0",
    "185.98.36.0",
    "35.235.16.8",
    "35.227.129.136",
    "35.234.176.136",
    "35.192.193.0",
    "35.205.0.8"
]


# initialize modules
app = Flask(__name__)
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
bcrypt = Bcrypt(app)
initialize_db(app.root_path)


# [PRE-REQUEST] always have user "logged in" (generate temp accounts)
@app.before_request
def verify_auth():
    username = session.get("username", None)
    user = fetch_user(username)
    if not username or not user:
        generate_temp_user()


# [PRE-REQUEST] log all requests (see if Unity is actaully doing their job)
@app.before_request 
def RequestLogger():
    log(
        "Requests",
        url = request.url,
        path = request.path,
        time = str(datetime.now()),
        unity = (request.remote_addr in UNITY_IPS),
        ip = request.remote_addr
    )


# generated/login temp account
def generate_temp_user():
    user = create_user(
        username = str(uuid4()),
        email = None,
        password = str(uuid4()),
        gems = 0
    )
    session["username"] = user["username"]
    session["gems"] = user["gems"]

# ask server for username
@app.route("/TempUser", methods=['POST'])
def TempUser():
    count = int(request.form["count"])
    for i in range(count):
        generate_temp_user()
    return redirect("/")


# ask server for username
@app.route("/Identity", methods=['POST'])
def identity():
    return session.get("username", "[None]")


# ask server for SID (document ID)
@app.route("/SID")
@none_required
def SID(user):
    return str(user.doc_id)


# debugger view (veiw/create users)
@app.route('/')
@none_required
def index(user):
    if user['username'] =='admin' or (os.environ.get("platform",None)=="replit"):
        # get all users
        users = fetch_users()
        # display page
        return render_template('dashboard.html', users=users, user=user)
    elif user['username'] !='admin':
        return render_template('login.html')


# Create a new account
@app.route('/CreateUser', methods=['POST'])
@none_required
def CreateUser(user):
    # validate form
    if "" in request.form.values():
        return "Error: Please Fill All Fields!"
        
    # validate username (length)
    if len(request.form['username']) >= 36:
        return "Error: Username too long"

    # inherit gems from previous account (IF its a temp account)
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
    if newUser==None:
        return "Could not create user"

    # log user in  
    session["username"] = request.form['username']
    session["gems"] = newUser["gems"]
    return f"User has been created!<br><a href='/'>Go Back<a>"


# Purge Old Temp Users
@app.route('/PurgeTempUsers', methods=['POST'])
@admin_required
def PurgeTempUsers(user):
    days = int(request.form['days'])
    purgeCount = purge_users(dayRange=days)
    return f"{purgeCount} temp users have been purged!<br><a href='/'>Go Back<a>"


# Increment Gems
@app.route('/GetGem', methods=['POST'])
@none_required
def GetGem(user):
    user["gems"] += 1
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# Calculate USD payed from in game Gems
def CalculatePayout(gemCount):
    '''
    TotalCut : amount of money Paypal is sending
    EntitledCut: amount of money player gets (after Paypal Takes Cut)
    '''
    SingleAdRevenue = 5 / 1000
    SingleGemRevenue = SingleAdRevenue / 5
    RevShare = 0.40
    TotalCut = gemCount * (SingleGemRevenue * RevShare)
    PaypalProcessingFee = (TotalCut * 0.029) + 0.30
    EntitledCut = TotalCut - PaypalProcessingFee
    TotalCut = int(TotalCut*100)/100
    EntitledCut = int(EntitledCut*100)/100
    return TotalCut, EntitledCut

# Calculate minimum gems needed to cover paypal processing and profit 1 cent
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
@email_required
def Cashout(user):
    # validate inputs
    try:
        email = user["email"]
        gemCount = int(request.form["gems"])
    except:
        return "Invalid Gem Count"
    
    # verify gem count
    if (user["gems"] < gemCount):
        return "You requested more gems than you have!"
    if gemCount < GEM_MINIMUM:
        return f"Processing fees outweigh your cashout ({GEM_MINIMUM} gems required)"
        
    # verify (unredeemed) ads have been watched (5 gems: 1 ad)

    # mark ads as redeemed / decrement gems
    

    # generate paypal cashout
    TotalPayout, EntitledPayout = CalculatePayout(gemCount)
    send_money(user["email"], TotalPayout)

    return f"Cashout of ${EntitledPayout:0.2f} sucessfully send to {email}"

# Increment Gems
@app.route('/GemCount')
@none_required
def GemCount(user):
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# TESTING PURPOSES ONLY
@app.route('/get_gem/<int:amount>')
@admin_required
def get_gem(amount, user):
    user["gems"] += amount
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    return redirect("/")



#https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks#Signing_the_Callback_URL
def verify_signature(parameters):
    # URL parameters (except the HMAC), alphabetical order, with commas.
    receivedSignature = parameters.pop("hmac", None)
    unhashed = ",".join([f"{key}={value}" for key,value in sorted(parameters.items())])
    
    # Generate Expected Hash
    expectedSignature = hmac.new(
        SECRET.UNITY_ANDRIOD_S2S.encode(),
        unhashed.encode(),
        hashlib.md5
    ).hexdigest()

    # Verify Hash
    return hmac.compare_digest(
        receivedSignature, 
        expectedSignature
    )


# UNITY S2S : Unity will use this route to tell us when users watch ads
@app.route('/S2S', methods=['GET'])
def WatchAd():    
    # Extract Parameters 
    parameters = request.args.to_dict()

    # Verify Parameters
    required_params = ['sid', 'oid', 'hmac']
    if not all(param in parameters for param in required_params):
        abort(422, "Missing required parameters")
    if not verify_signature(parameters):
        abort(401, "Invalid Signature")


    print(parameters)
    user = fetch_user(int(parameters["sid"]))
    print(user)
    if user==None:
        abort(400, "Invalid user SID")
    
    # Store Ad in database (as unredeemed)
    record_ad(
        **parameters,
        redeemed = False
    )
    return {'status': 'success'}


# see the ads that the current user 
@app.route('/SeeMyAds')
@admin_required
def SeeMyAds(user):
    return jsonify(fetch_ads(user.doc_id))

# see the ads that the current user 
@app.route('/SeeAllAds')
@admin_required
def SeeAllAds(user):
    return jsonify(fetch_ads())



# see the ALL request logs (S2S logs)
@app.route('/RequestLog')
@admin_required
def RequestLog(user):
    return jsonify(fetch_all('Requests'))



# take over temp_user account (fake "registration")
@app.route('/Login', methods=['POST'])
@temp_required
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
        delete_user(username) 
    return redirect('/')


# **New route to delete a user**
@app.route('/DeleteUser', methods=['POST'])
def delete_user_route():
    username = request.form['username']
    delete_user(username)
    return f"User [{username}] has been deleted<br><a href='/'>Go Back<a>"


@app.route('/Logout', methods=['POST'])
def logout():
    session.pop("username", None)
    return f"You are logged out<br><a href='/'>Go Back<a>"


if __name__ == '__main__':
    app.run(debug=True)
