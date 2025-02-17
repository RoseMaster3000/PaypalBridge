from flask import Flask, render_template, request, redirect, session, jsonify, abort, make_response
from flask_bcrypt import Bcrypt
from datetime import datetime
from uuid import uuid4
from urllib.parse import unquote, urlparse
import hmac
import hashlib
import os

from PaypalBridge.paypal import create_payout
from PaypalBridge import SECRET
from PaypalBridge.database.tinydb import *


# initialize modules
app = Flask(__name__)
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
bcrypt = Bcrypt(app)
initialize_db(app.root_path)
from PaypalBridge.decorators import *



# [PRE-REQUEST] always have user "logged in" (generate temp accounts)
@app.before_request
def verify_auth():
    username = session.get("username", None)
    user = fetch_user(username)
    if not username or not user:
        generate_temp_user()

# generated/login temp account
def generate_temp_user():
    user = create_user(
        username = str(uuid4()),
        email = None,
        password = str(uuid4()),
        gems = 0,
        total_cashout = 0
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
    if user['username'] =='admin' or app.debug:
        # get all users
        users = fetch_users()
        # display page
        return render_template('dashboard.html', users=users, user=user)
    elif user['username'] !='admin':
        return render_template('login.html')



def convert_epoch(epoch_time):
    datetime_object = datetime.fromtimestamp(epoch_time)
    return datetime_object.strftime("%Y-%m-%d %H:%M:%S")  # Customize the format as needed

def ad_preview(user):
    all_ads = fetch_ads(user.doc_id, redeemed=None)
    all_i = 0
    all_r = 0
    redeemed_i = 0
    redeemed_r = 0


    print(user.doc_id, len(all_ads))

    for ad in all_ads:
        if ad.get("type") == "Rewarded":
            all_r += 1
            if ad.get("redeemed"):
                redeemed_r += 1
        if ad.get("type") == "Interstitial":
            all_i += 1
            if ad.get("redeemed"):
                redeemed_i += 1

    return f"{redeemed_r}/{all_r}" , f"{redeemed_i}/{all_i}"

# route to fetch a list of all users
@app.route('/api/users', methods=['GET'])
@admin_required
def GetAllUsers(user):
    users = fetch_users()
    for u in users:
        rewarded, intersitial = ad_preview(u)
        u["total_cashout"] = f"{u['total_cashout']:0.2f}"
        u["created_at"] = convert_epoch(u["created_at"])
        u["rewarded"] = rewarded
        u["intersitial"] = intersitial
    return jsonify(users)


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
        gems = inheritedGems,
        total_cashout = 0
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
    # intersitial ad value
    SingleRewarded = 0.04 / 35   # sample from ad dashboard
    SingleInterstitial = SingleRewarded / 10
    if SingleInterstitial >= (5 / 10000):
        print(SingleInterstitial)
        print(5/10000)
        raise Exception("Interstitial Value too low")

    SingleGemRevenue = SingleInterstitial / 5
    RevShare = 0.70 # percent the user gets
    TotalCut = gemCount * (SingleGemRevenue * RevShare)
    if (TotalCut * 0.02 > 0.25):
        PaypalProcessingFee = TotalCut * 0.02
    else:
        PaypalProcessingFee = 0.25
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
        # print(gems,EntitledPayout)
    return gems
GEM_MINIMUM = CalculateMinimumGems()
print("GEM MINIMUM:", GEM_MINIMUM)


# mark ad as redeemed = True in TinyDB
def redeem(ad):
    update_ad(ad, redeemed=True)


# minimal number of intersitial / rewarded ads to cover gemCount
# 1 intersitial == 1 gem (red)
# 1 rewarded == 10 gems  (green)
def minimal_ad_count(r, i, gems, debug=False):
    usedRewarded = 0
    usedInterstitial = 0

    while gems > 0:

        # use interstial ads to get it round 10s
        if (gems % 10 != 0 and i > 0):
            usedInterstitial += 1
            i -= 1
            gems -= 1
        # use rewarded ads (if possible)
        elif (r > 0):
            usedRewarded += 1
            r -= 1
            gems -= 10
        # use interstial if we run out of rewarded
        elif (i > 0):
            usedInterstitial += 1
            i -= 1
            gems -= 1
        # we dont have enough ads to cover the gems
        else:
            return None, None
        # debugger
        if (debug):
            print(gems, usedRewarded,usedInterstitial, (gems%10))
            input()

    return usedRewarded, usedInterstitial


# find subset of ads == the gems you want
# return False if not enough ads for gemCount 
def redeem_ads(ads, gemCount):
    # collate our ads   
    intersitial = []
    rewarded = []
    for ad in ads:
        if "Interstitial" in ad["adUnitID"]:
            intersitial.append(ad)
        elif "Rewarded" in ad["adUnitID"]:
            rewarded.append(ad)


    # Calculate minimal ad count needed to redeem gems
    rewarded_used, intersitial_used = minimal_ad_count(
        i = len(intersitial),
        r = len(rewarded),
        gems = gemCount
    )

    # EJECT if not enough ads to cover gem cashout
    if rewarded_used == None:
        return False

    # Mark ads as redeemed
    for i in range(rewarded_used):
        redeem(rewarded[i])
    for i in range(intersitial_used):
        redeem(intersitial[i])

    # return --> SUCCESS
    return True




@app.route("/Cashout/<gemCount>")
def PreviewCashout(gemCount:int):
    if gemCount < GEM_MINIMUM:
        return f"Processing fees outweigh your cashout ({GEM_MINIMUM} gems required)"
    else:
        return CalculatePayout(gemCount)

# Cashout Gems (form["gems"] + logged in)
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
        
    # verify (unredeemed) ads have been watched
    ads = fetch_ads(user.doc_id, redeemed=False)

    # mark ads as redeemed / decrement gems
    redeem_sucess = redeem_ads(ads, gemCount)

    # S2S callback hasnt come (OR player has hacked illegal gems)
    if not redeem_sucess:
        return "Ad revenue is still processing, please try again in a few hours."
    
    # generate paypal cashout
    TotalPayout, EntitledPayout = CalculatePayout(gemCount)
    create_payout(email, EntitledPayout)

    # increment cashout total (track cashout total in our database)
    increment_cashout(user, EntitledPayout)

    return f"Cashout of ${EntitledPayout:0.2f} successfully send to {email}"

# Get current balance (gem count)
@app.route('/GemCount')
@none_required
def GemCount(user):
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# TESTING PURPOSES ONLY, Increment Gems
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


# https://dcherevatsky.pythonanywhere.com/S2S?oid=1737946872029&sid=101&hmac=fcd620d061910db14784f00f5d7af63c
@app.route('/Fake/S2S', methods=['GET'])
@log_request
@admin_required
def WatchFakeAd(user):
    record_ad(
        userID = user.doc_id,
        oid = str(uuid4()),
        adUnitID = "Fake_Rewarded_Ad",
        type = "Rewarded",
        redeemed = False
    )
    return redirect("/")


# UNITY S2S : Unity will use this route to tell us when users watch ads
@app.route('/S2S', methods=['GET'])
@log_request
def WatchAd():
    # Extract Parameters 
    parameters = request.args.to_dict()

    # Verify Parameters
    required_params = ['sid', 'oid', 'hmac']
    if not all(param in parameters for param in required_params):
        abort(400, "Missing required parameters")
    if not verify_signature(parameters):
        abort(403, "Invalid Signature")

    # Extract Parameters
    oid = parameters["oid"]
    adUnitID = parameters["sid"].split()[1]
    userID = int(parameters["sid"].split()[0])
    user = fetch_user(UserID)

    # Verify User
    if user==None:
        abort(400, "Invalid user SID")
    
    # Store Ad in database (as unredeemed)
    record_ad(
        userID = userID,
        oid = oid,
        adUnitID = adUnitID,
        type = "Rewarded" if "Rewarded" in adUnitID else "Interstitial",
        redeemed = False
    )
    # Report Success (https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks#CallbackResponse)
    return "1", 200


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
@none_required
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
