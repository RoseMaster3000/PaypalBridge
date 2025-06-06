from flask import Flask, render_template, request, redirect, session
from flask import jsonify, abort, make_response, send_from_directory
from flask_bcrypt import Bcrypt
import datetime
from uuid import uuid4
from urllib.parse import unquote, urlparse
import hmac
import hashlib
import os

from PaypalBridge.paypal import create_payout
from PaypalBridge import SECRET
from PaypalBridge.database.tinydb import *
from PaypalBridge.ecpm import get_recent_ecpm

from werkzeug.utils import secure_filename
import magic


# initialize modules
app = Flask(__name__) 
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['DATABASE_FOLDER'] = os.path.join(os.getcwd(), 'DatabaseStorage')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATABASE_FOLDER'], exist_ok=True)
bcrypt = Bcrypt(app)
initialize_db(app)
from PaypalBridge.decorators import *


# [PRE-REQUEST] always have user "logged in" (generate temp accounts)
@app.before_request
def verify_auth():
    username = session.get("username", None)
    user = fetch_user(username)
    if not user:
        generate_temp_user()

# generated/login temp account
def generate_temp_user():
    user = create_user(
        username = str(uuid4()),
        email = None,
        password = str(uuid4()),
        gems = 0,
        bonus = 0,
        rewarded = 0,
        interstitial = 0,
        total_cashout = 0,
        children = [],
        earnings = 0,
        cashouts = []
    )
    session["username"] = user["username"]
    session["gems"] = user["gems"]


@app.route("/ResetAccount", methods=['GET'])
@none_required
def ResetAccount(user):
    session["gems"] = 0
    user["gems"] = 0
    user["bonus"] = 0
    user["rewarded"] = 0
    user["interstitial"] = 0
    user["total_cashout"] = 0
    user["earnings"] = 0
    user["children"] = []
    user["cashouts"] = []
    update_user(user["username"], **user)
    return redirect("/")

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
    cookies = request.cookies
    print("Received cookies:", dict(cookies))
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
        websiteRevenue = fetch_revenue("website")
        playerRevenue = fetch_revenue("player")
        grossRevenue = fetch_revenue("gross")
        # display page
        return render_template(
            'dashboard.html',
            users=users,
            user=user,
            websiteRevenue= f"${websiteRevenue:,.02f}",
            playerRevenue= f"${playerRevenue:,.02f}",
            grossRevenue= f"${grossRevenue:,.02f}",
            interstitialECPM = f"${get_recent_ecpm('interstitial'):,.02f}",
            rewardedECPM = f"${get_recent_ecpm('rewarded'):,.02f}"
        )
    elif user['username'] !='admin':
        return render_template('login.html')


@app.route("/reset_revenue/<target>")
@admin_required
def reset_cash_counter(user, target):
    set_revenue(target, 0)
    return redirect("/")


def convert_epoch(epoch_time):
    if type(epoch_time)==str: return epoch_time
    datetime_object = datetime.fromtimestamp(int(epoch_time))
    return datetime_object.strftime("%Y-%m-%d %H:%M:%S")  # Customize the format as needed


# route to fetch a list of all users
@app.route('/api/users', methods=['GET'])
@admin_required
def GetAllUsers(user):
    users = fetch_users()
    for u in users:
        u["earnings"] = f"${u['earnings']:0.5f}"
        u["total_cashout"] = f"${u['total_cashout']:0.2f}"
        u["created_at"] = convert_epoch(u["created_at"])
        u["sid"] = u.doc_id
    return jsonify(users)


# Create a new account
@app.route('/Register', methods=['POST'])
@app.route('/CreateUser', methods=['POST'])
@none_required
def CreateUser(user):
    # validate form
    if "" in request.form.values():
        return "Error: Please Fill All Fields!"
    
    # validate username
    print(request.form['username'])
    print(len(request.form['username']))
    if len(request.form['username']) >= 36 and len(request.form['username']) <= 0:
        return "Error: Username must be 1-36 characters long"
    if fetch_user(request.form['username']) != None:
        return "Error: Username is taken"
    if not request.form['username'].isalnum():
        return "Error: Username must be alphanumeric"

    # validate email
    if fetch_user_email(request.form['email']) != None:
        return "Error: Email already is registered to an account"

    # valiate password
    if len(request.form['password']) < 8:
        return "Error: Password must be 8 characters long"

    # claim temporary account (update new values)
    success = update_user(
        user = user["username"],
        username = request.form['username'],
        email = request.form['email'],
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8'),
    )
    if not success:
        return "Could not create user"

    # log user in  
    session["username"] = request.form['username']
    return f"User has been created!"


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
    user["gems"] += int(request.form["gems"])
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# watch bonus ad (rewarded ad) worth 50 gems
@app.route('/GetBonus', methods=['POST'])
@none_required
def GetBonusGem(user):
    user["bonus"] += int(request.form["gems"])
    update_user(user["username"], **user)
    session["bonus"] = user["bonus"]
    if user['bonus'] == 1:
        return f"{user['bonus']} Bonus Gem"
    else:
        return f"{user['bonus']} Bonus Gems"


# Calculate USD payed (based on hardcoded value for ads)
# (OLD method where rewarded/intersitial ads have FIXED values)
def CalculatePayoutFixed(gemCount):
    '''
    TotalCut : amount of money PayPal is sending
    EntitledCut: amount of money player gets (after PayPal Takes Cut)
    '''
    # interstitial ad value
    SingleRewarded = 0.04 / 35   # sample from ad dashboard
    SingleInterstitial = SingleRewarded / 10
    if SingleInterstitial >= (5 / 10000):
        print(SingleInterstitial)
        print(5/10000)
        raise Exception("Interstitial Value too low")

    SingleGemRevenue = SingleInterstitial / 5
    TotalRevenue = gemCount * SingleGemRevenue
    return CalculateCuts(TotalRevenue)

# Calculate USD payed (based on player's performance in game & moving eCPM)
# "gamerScore" (gems you are cashing out ÷ number of gems you could have earned maximally, based on ads served)
# (New method, collecting earnings, tracked in S2S callbacks with eCPM)
def CalculatePayoutSkill(user, gemCount):
    totalEarnings = CalulateEarnings(user, gemCount)
    return CalculateCuts(totalEarnings)
    

def CalulateEarnings(user, gemCount):
    if gemCount==0: return 0
    gemMaximum = (user["interstitial"]*5) + (user["rewarded"]*50)
    gamerScore = gemCount / gemMaximum if gemMaximum else 0
    return user["earnings"] * gamerScore # earnings (based on game performance) BEFORE processing fees


# calculate generic market value of single gem (given current eCPM)
def MarketGemValue():
    interstitialValue = get_recent_ecpm("interstitial") / 1000
    rewardedValue = get_recent_ecpm("rewarded") / 1000
    singleGemValue = (interstitialValue + rewardedValue) / 55
    return singleGemValue


def CalculateCuts(TotalRevenue):
    PlayerShare = 0.70 # percent the user gets
    PlayerCut = TotalRevenue * PlayerShare
    if (PlayerCut * 0.02 > 0.25):
        PaypalProcessingFee = PlayerCut * 0.02 # 2% processing (domestic)
    else:
        PaypalProcessingFee = 0.25 # 25¢ processing (international)
    EntitledCut = PlayerCut - PaypalProcessingFee
    PlayerCut = int(PlayerCut*100)/100
    EntitledCut = int(EntitledCut*100)/100
    AdminCut = TotalRevenue - PaypalProcessingFee - EntitledCut
    return PlayerCut, EntitledCut, AdminCut


# Calculate # of gems needed to make at least 1 cent
# (First use user's earnings / gems, then see how many more gems they would need)
# (will add "~" symbol need additional theoretical market value gems)
def CalculateGemsNeeded(user, gemCount):
    gemsLeft = max(user["gems"] - gemCount, 0)
    gemsNeeded = gemCount
    totalEarnings = CalulateEarnings(user, gemCount)
    entitledCut = 0
    projectedGems = ""
    singleGemValue = MarketGemValue()
    fakeGems = 0

    print(totalEarnings, gemsLeft, fakeGems)

    while entitledCut < 0.01:    
        # First use gems the user has already earned
        if gemsLeft > 0:
            gemsNeeded += 1
            gemsLeft -= 1
            totalEarnings = CalulateEarnings(user, gemCount)
        # or use theoretical additional market rate gems
        else:
            gemsNeeded += 1
            fakeGems += 1
            projectedGems = "~"
            totalEarnings += singleGemValue
        # Calculate new cut
        _, entitledCut, _ = CalculateCuts(totalEarnings)

    print(totalEarnings, gemsLeft, fakeGems)
    return f"{projectedGems}{gemsNeeded}"



# minimal number of interstitial / rewarded ads to cover gemCount
# 1 interstitial == 1 gem (red)
# 1 rewarded == 10 gems  (green)
def minimal_ad_count(r, i, gems, debug=False):
    usedRewarded = 0
    usedInterstitial = 0

    while gems > 0:
        # use rewarded ads (if possible)
        if (gems >= 50 and r > 0):
            usedRewarded += 1
            r -= 1
            gems -= 50
        # use interstitial ads (if possible)
        elif (gems >= 5 and i > 0):
            usedInterstitial += 1
            i -= 1
            gems -= 5
        # use rewarded ads (back up)
        elif (r > 0):
            usedRewarded += 1
            r -= 1
            gems -= 50
        # we dont have enough ads to cover the gems
        else:
            return None, None
        # debugger
        if (debug):
            print(gems, usedRewarded,usedInterstitial)
            input()

    return usedRewarded, usedInterstitial


# find subset of ads == the gems you want
# return False if not enough ads for gemCount 
def redeem_ads(userID, gemCount):
    user = fetch_user(userID)

    # Calculate minimal ad count needed to redeem gems
    rewarded_used, interstitial_used = minimal_ad_count(
        i = user["interstitial"],
        r = user["rewarded"],
        gems = gemCount
    )

    # EJECT if not enough ads to cover gem cashout
    if rewarded_used == None:
        return False, user

    # Decrement ad count ("redeem" ads by deleting them)
    user["interstitial"] -= interstitial_used
    user["rewarded"] -= rewarded_used
    success = update_user(user.doc_id, **user)

    # done!
    return True, user


@app.route('/PreviewCashout', methods=['POST'])
@none_required
def PreviewCashoutPost(user):
    data = {
        "gemCount": 0,
        "baseGem": user.get("gems",0),
        "bonusGem": user.get("bonus",0),
        "totalGem": user.get("gems",0) + user.get("bonus",0),
        "payout": "$0.00",
        "message": "..."
    }

    # Error: you must login
    if user.get("email", None) == None:
        data["message"] = "To cashout, login or register with an email associated with a PayPal account."
        return jsonify(data)

    # Error: Client provided strange gem count
    try:
        data["gemCount"] = int(request.form["gems"])
    except:
        data["message"] = "Error: Invalid gem count provided to server"
        return jsonify(data)

    # Error: Asking for more gems than you have
    if data["gemCount"] > data['totalGem']:
        data["message"] = "Error: Can not cashout {gemCount:,} gems, you only have {totalGem:,}".format(**data)
        return jsonify(data)

    # Calcualte Payouts
    _, EntitledCut, AdminCut = CalculatePayoutSkill(user, data["gemCount"] )
    data["payout"] = f"${EntitledCut:,.02f}"
    # Invalid cashout
    if EntitledCut <= 0:
        gemsNeeded = CalculateGemsNeeded(user, data["gemCount"])
        data["message"] = f"Processing fees outweigh your cashout, you need {gemsNeeded} gems to cashout (at today's rate)"
        data["payout"] = "$0.00"
    # Standard Cashout
    else:
        data["message"] = "A {gemCount:,} gem cashout would result in a ${payout} payout to PayPal!".format(**data)
    return jsonify(data)


# decrment base gems (then bonus gems if necessary)
# return T/F if not enough gems
def redeem_gems(user, gemCount):
    # use bonus gems first (if possible)
    if user["bonus"] > 0 and gemCount > 0:
        if user["bonus"] >= gemCount:
            user["bonus"] = user["bonus"] - gemCount
            gemCount = 0
        else:
            gemCount = gemCount - user["bonus"]
            user["bonus"] = 0

    # use base gems second (if possible)
    if user["gems"] > 0 and gemCount > 0:
        if user["gems"] >= gemCount:
            user["gems"] = user["gems"] - gemCount
            gemCount = 0
        else:
            gemCount = gemCount - user["gems"]
            user["gems"] = 0

    # verify gems have been covered
    if gemCount == 0:
        update_user(user["username"], **user)
        return True, user
    else:
        return False, user


# Cashout Gems (form["gems"] + logged in)
@app.route('/Cashout', methods=['POST'])
@email_required
def Cashout(user):
    # validate inputs
    try:
        email = user["email"]
        gemCount = int(request.form["gems"])
    except:
        return jsonify({"success":False, "message": "Invalid Gem Count"})
    
    # verify gem count
    if ((user["gems"]+user["bonus"]) < gemCount):
        return "You requested more gems than you have!"

    # verify payout ()
    TotalCut, EntitledCut, AdminCut = CalculatePayoutSkill(user, gemCount)
    if EntitledCut <= 0:
        gemsNeeded = CalculateGemsNeeded(user, gemCount)
        return jsonify({"success":False, "message": f"Processing fees outweigh your cashout, you need {gemsNeeded} gems to cashout (at today's rate)"})
    
    # mark ads as redeemed (verify S2S callbacks (detects illegal gems / too fast cashout?)
    redeem_success, user = redeem_ads(user, gemCount)
    if not redeem_success:
        return jsonify({"success": False, "message": "Ad revenue is still processing, please try again in a few hours."})

    # decrement gems (consume bonus if necessary)
    redeem_success, user = redeem_gems(user, gemCount)
    if not redeem_success:
        return jsonify({"success": False, "message": "Insufficient gems? Gem count has de-synced?"})

    # Process payout (PayPal)
    create_payout(email, EntitledCut)

    # decrement earnings + log cashout in our database
    cashout_success, user = log_cashout(
        user,
        gemCount,
        TotalCut,
        EntitledCut,
        AdminCut
    )
    return jsonify({"success": True, "message": f"Cashout of ${EntitledCut:0.2f} successfully send to {email}"})

@app.route("/CashoutHistory/")
@none_required
def CashoutHistorySelf(user):
    return CashoutHistory(user["username"])

@app.route("/CashoutHistory/<username>")
@admin_required
def CashoutHistoryOther(user, username):
    return CashoutHistory(username)

def CashoutHistory(username):
    targetUser = fetch_user(username)
    for c in targetUser["cashouts"]:
        c["time"] = convert_epoch(c["time"])
    return jsonify(targetUser["cashouts"])


# Return all data on User
@app.route("/GetUserEarnings")
@none_required
def GetUserInfo(user):
    if "total_cashout" in user:
        return f"{user['total_cashout']:.02f}"
    else:
        return "0.00"
    

# Get current balance (gem count)
@app.route('/GemCount')
@none_required
def GemCount(user):
    return f"{user['gems']}"


# TESTING PURPOSES ONLY, Increment Gems
@app.route('/get_gem/<int:amount>')
@admin_required
def get_gem(amount, user):
    user["gems"] += amount
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    return redirect("/")


# TESTING PURPOSES ONLY, Increment Gems
@app.route('/get_bonus_gem/<int:amount>')
@admin_required
def get_bonus_gem(amount, user):
    user["bonus"] += amount
    update_user(user["username"], **user)
    session["bonus"] = user["bonus"]
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
@app.route('/Fake/S2S/Rewarded/<int:count>', methods=['GET'])
@admin_required
def WatchFakeRewarded(user, count):
    record_rewarded(user, count)
    return redirect("/")


# https://dcherevatsky.pythonanywhere.com/S2S?oid=1737946872029&sid=101&hmac=fcd620d061910db14784f00f5d7af63c
@app.route('/Fake/S2S/Interstitial/<int:count>', methods=['GET'])
@admin_required
def WatchFakeInterstitial(user, count):
    record_interstitial(user, count)
    return redirect("/")


# Simulate Playing the game (watching around of ads / collecting perfect 55 gem)
@app.route('/Fake/S2S/AdRound/<int:count>', methods=['GET'])
@admin_required
def WatchFakeAdRound(user, count):
    record_ad_round(user.doc_id, count)
    return redirect("/")


# UNITY S2S : Unity will use this route to tell us when users watch ads
@app.route('/S2S', methods=['GET'])
@log_request
def WatchAd():
    try:
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
        delimitter = " " if " " in parameters["sid"] else "+"
        userID = int(parameters["sid"].split(delimitter)[0])
        adUnitID = parameters["sid"].split(delimitter)[1]
        user = fetch_user(userID)

        # Verify User
        if user==None:
            abort(400, "Invalid user SID")
        
        # Store Ad in database (as unredeemed)
        if "Rewarded" in adUnitID:
            record_rewarded(user)
        else:
            record_interstitial(user)

        # Report Success (https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks#CallbackResponse)
        return "1", 200
    except Exception as e:
        log(
            "Requests",
            url = request.url,
            error = str(e)
        )
        return "1", 200


# see the ads that the current user 
@app.route('/SeeAllAds/<username>')
@admin_required
def SeeMyAds(user, username):
    targetUser = fetch_user(username)
    return jsonify(fetch_ads(targetUser.doc_id))

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
    oldUser = user
    newUser = fetch_user(request.form['username'])

    # verify user
    if newUser==None:
        return f"User Does not Exist"
    
    # verify password
    if not bcrypt.check_password_hash(newUser['password'], request.form['password']):
        return f"Password is Incorrect"

    # if old user is TEMPORARTY ACCOUNT with GEMS
    oldGems = oldUser.get("gems",0) + oldUser.get("bonus",0)
    if oldUser.get("email",None) == None and oldGems > 0:
        # new user takes old user's ads / gems
        adopt_user(
            parent = newUser,
            child = oldUser
        )

    # log user in  
    session["username"] = newUser["username"]
    session["gems"] = newUser["gems"]
    return f"Logged in Successfully <br><a href='/'>Go Back</a>"


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
    return f"You are logged out"

#----wallet_status api is route to anable disable wallet button in unity----
# Initial state
WALLET_BUTTON_VISIBLE = False
WALLET_BUTTON_INTERACTABLE = False
 
@app.route('/api/wallet_status')
def wallet_status():
    # Interactable only if visible
    interactable = WALLET_BUTTON_INTERACTABLE if WALLET_BUTTON_VISIBLE else False
    return jsonify({
        "visible": WALLET_BUTTON_VISIBLE,
        "interactable": interactable
    })
 
@app.route('/update_wallet_status', methods=['GET', 'POST'])
def update_wallet_status():
    global WALLET_BUTTON_VISIBLE, WALLET_BUTTON_INTERACTABLE
    success = False
 
    if request.method == 'POST':
        WALLET_BUTTON_VISIBLE = 'visible' in request.form
        WALLET_BUTTON_INTERACTABLE = 'interactable' in request.form and WALLET_BUTTON_VISIBLE
        success = True  # Show success message
  

    return render_template('wallet_status.html',
                           WALLET_BUTTON_VISIBLE=WALLET_BUTTON_VISIBLE,
                           WALLET_BUTTON_INTERACTABLE=WALLET_BUTTON_INTERACTABLE,
                           success=success)



if __name__ == '__main__':
    app.run(debug=True)
