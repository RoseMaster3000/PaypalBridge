from flask import Flask, render_template, request, redirect, session
from flask import jsonify, abort, make_response, send_from_directory
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
from uuid import uuid4
from urllib.parse import unquote, urlparse
import hmac
import hashlib
import os
from werkzeug.utils import secure_filename
import magic
from PaypalWebsite.paypal import create_payout
from PaypalWebsite import SECRET
from PaypalWebsite.database.tinydb import *
from PaypalWebsite.ecpm import get_recent_ecpm, initialize_ecpm

ADMINS = ["admin", "dimad"] # to add more users(admins to "admin, "dima", "wertyr")

# Initialize Modules
app = Flask(__name__) 
bcrypt = Bcrypt(app)
def isDeveloper(): return session.get("username", None) in ADMINS or app.debug
limiter = Limiter(
    get_remote_address,
    app = app,
    default_limits = ["3000 per hour"], # ~ 1/second
    storage_uri = "memory://", # redis or monogo for production...
    default_limits_exempt_when = isDeveloper
)
app.config['SECRET_KEY'] = SECRET.FLASK_KEY

# Initialize Storage Folders
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'uploads')
app.config['DATABASE_FOLDER'] = os.path.join(app.root_path, '..', 'DatabaseStorage')
print(app.config['UPLOAD_FOLDER'])
print(app.config['DATABASE_FOLDER'])
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATABASE_FOLDER'], exist_ok=True)
initialize_db(app)
initialize_ecpm(app)


# initialize custom decorators
from PaypalWebsite.decorators import *


# [PRE-REQUEST] always have user "logged in" (generate temp accounts)
@app.before_request
def verify_auth():
    path = request.path

    # Skip static files
    if path.startswith('/static/'):
        return

    # Skip S2S (Unity Ads servers)
    if path.startswith('/S2S') or path.startswith('/Fake/S2S'):
        return

    # Skip Identity (Identity must decide whether to create temp user)
    if path.startswith('/Identity'):
        return

    # If session already has a valid user, keep it
    username = session.get("username")
    if username and fetch_user(username) is not None:
        return

    # Otherwise create a temp user
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
    username = session.get("username")

    # CASE 1 — No username in session → create a new temp user
    if not username:
        username = generate_temp_username()

        # Only create user if not already in DB
        if not fetch_user(username):
            create_user(username)

        session["username"] = username
        return username

    # CASE 2 — Username exists in session but user was deleted
    user = fetch_user(username)
    if user is None:
        username = generate_temp_username()

        if not fetch_user(username):
            create_user(username)

        session["username"] = username
        return username

    # CASE 3 — Valid user
    return username


# ask server for SID (document ID)
@app.route("/SID")
@none_required
def SID(user):
    if not user:
        return "-1"
    return str(user.doc_id)


# debugger view (veiw/create users)
@app.route('/')
@none_required
def index(user):
    if isDeveloper():
        return redirect("/Dashboard")
    else:
        return redirect("/Login")


@app.route('/Dashboard', methods=['GET'])
@admin_required
def dashboard_page(user):
    # get all users
    users = fetch_users()
    websiteRevenue = fetch_revenue("website")
    playerRevenue = fetch_revenue("player")
    grossRevenue = fetch_revenue("gross")
    paypalMode = get_paypal_mode() # either "sandbox" or "live"
    overrideEnabled = get_override_status() #cashout button override

# eCPM values
    
    

    interstitial_ecpm = get_recent_ecpm("interstitial") or 0.0  # e.g. $1.20
    rewarded_ecpm = get_recent_ecpm("rewarded") or 0.0     # e.g. $10.00

    # Total ads watched
    total_ads = sum(u["interstitial"] + u["rewarded"] for u in users)

    # Gem value calculation
    interstitial_value = interstitial_ecpm / 1000
    rewarded_value = rewarded_ecpm / 1000
    gem_value = (interstitial_value + rewarded_value) / 55  # 55 gems per ad round

    # display page
    return render_template(
        'dashboard.html',
        users=users,
        user=user,
        paypalMode = paypalMode,
        cashoutOverride=overrideEnabled,
        websiteRevenue= f"${websiteRevenue:,.02f}",
        playerRevenue= f"${playerRevenue:,.02f}",
        grossRevenue= f"${grossRevenue:,.02f}",
        interstitialECPM = f"${get_recent_ecpm('interstitial'):,.02f}",
        rewardedECPM = f"${get_recent_ecpm('rewarded'):,.02f}",
        totalAds=total_ads,
        gemValue=f"${gem_value:,.5f}"

    )


@app.route('/Login', methods=['GET'])
@none_required
def login_page(user):
    return render_template('login.html')


@app.route("/reset_revenue/<target>")
@admin_required
def reset_cash_counter(user, target):
    set_revenue(target, 0)
    return redirect("/")


def convert_epoch(epoch_time):
    if type(epoch_time)==str: return epoch_time
    datetime_object = datetime.fromtimestamp(int(epoch_time))
    return datetime_object.strftime("%m/%d/%Y %H:%M:%S")  # Customize the format as needed


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
    response = make_response(jsonify(users))
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


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
@limiter.limit("2/second", exempt_when=isDeveloper)
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
    gamerScore = min(gemCount / gemMaximum, 1) if gemMaximum else 0
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

#----for paypal new add if not delete
@app.route('/set-paypal-mode', methods=['POST'])
def set_paypal_mode_route():
    mode = request.json.get('mode')
    if mode in ['sandbox', 'live']:
        set_paypal_mode(mode)
        return jsonify({'status': 'success', 'mode': mode})
    return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400

@app.route('/get-paypal-mode', methods=['GET'])
def get_paypal_mode_route():
    mode = get_paypal_mode()
    return jsonify({'mode': mode})
    # end of new add if not delete lines 470-483


# Cashout Gems (form["gems"] + logged in)
@app.route('/Cashout', methods=['POST'])
@email_required
@limiter.limit("1/day", exempt_when=isDeveloper)
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

    # verify payout (processing fees)
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
    # modifed lines:  origina was
    # create_payout(email, EntitledCut)
    paypal_mode = get_paypal_mode()
    create_payout(email, EntitledCut, mode=paypal_mode)

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
    if not user:
        return "0"
    return f"{user.get('gems', 0)}"


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
@limiter.exempt
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

    # If you are an admin + this is in a web browser, goto Dashboard
    if isDeveloper() and isBrowser(request):
        return redirect("/Dashboard")
    else:
        return f"Logged in Successfully"


def isBrowser(request):
    user_agent = request.headers.get('User-Agent', 'Unknown')
    browsers = ['Mozilla', 'Chrome', 'Safari']
    if user_agent == 'Unity':
        return False
    elif any([b in user_agent for b in browsers]):
        return True
    else:
        return None



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

"""
script_status = {"enabled": True}
 

@app.route('/set_script_status', methods=['POST'])
def set_script_status():
    data = request.get_json()
    script_status["enabled"] = data.get("enabled", True)
    return jsonify({"message": f"Script {'enabled' if script_status['enabled'] else 'disabled'}"})
 
@app.route('/script_status', methods=['GET'])
def get_script_status():
    return jsonify(script_status)"""



if __name__ == '__main__':
    app.run(debug=True)

@app.route("/Ping")
def ping():
    return "SERVER VERSION 7"

@app.route("/DebugIdentity", methods=['GET'])
def debug_identity():
    return {
        "cookies": dict(request.cookies),
        "session": dict(session),
        "session_username": session.get("username"),
        "user_exists": fetch_user(session.get("username")) is not None
    }