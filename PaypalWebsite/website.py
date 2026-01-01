from flask import Flask, render_template, request, redirect, session
from flask import jsonify, abort, make_response, send_from_directory
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
import time
from uuid import uuid4
import uuid
from urllib.parse import unquote, urlparse
import hmac
import hashlib
import os
from werkzeug.utils import secure_filename
import magic
from PaypalWebsite.paypal import create_payout
from PaypalWebsite import SECRET
#from PaypalWebsite.database.tinydb import *
from PaypalWebsite.database.tinydb import get_paypal_mode
from PaypalWebsite.database.tinydb import log_cashout
from PaypalWebsite.ecpm import initialize_ecpm, get_recent_ecpm
from PaypalWebsite import calculations
from PaypalWebsite.isDevelopers import isDeveloper
from PaypalWebsite.blueprint_appad import appad
from PaypalWebsite.blueprint_UnityCashoutButton import cashout_button
from PaypalWebsite.blueprint_CashoutHistory import web_cashoutHistory
from PaypalWebsite.blueprint_UnityWalletButton import wallet_button
import traceback
from PaypalWebsite.database.tinydb import (
    adopt_user,
    create_user,
    fetch_user,
    delete_user,
    fetch_users,
    fetch_user_email,
    update_user,
    get_paypal_mode,
    log_cashout,
    set_revenue,
    fetch_revenue,
    convert_epoch,
    initialize_db,
    get_override_status,
    set_override_status,
    purge_users,
    record_ad_round,
    get_age_restriction_enabled,
    get_minimum_age,
    get_user_age,
    get_hide_all_buttons
)
# initialize custom decorators
from PaypalWebsite.decorators import (
none_required, admin_required,
email_required, log_request, temp_required)
 
print("=== FLASK SERVER STARTED ===")


# Initialize Modules
app = Flask(__name__) 
app.secret_key = SECRET.FLASK_KEY
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@app.after_request
def debug_response(response):
    print("=== FINAL RESPONSE HEADERS ===")
    print(response.headers)
    return response

calculations.register_payout_routes(app)

# Register Blueprint for blueprint_appad.py
app.register_blueprint(appad)
appad.config = app.config  #Give the blueprint access to the main app's config
# Register Blueprint for blueprint_UnityCashoutButton.py
app.register_blueprint(cashout_button)
# Register Blueprint for blueprint_cashoutHistory.py
app.register_blueprint(web_cashoutHistory)
# Register Blueprint for blueprint_UnityWalletButton.py
app.register_blueprint(wallet_button)

bcrypt = Bcrypt(app)

#app.config['SECRET_KEY'] = SECRET.FLASK_KEY

# Initialize Storage Folders
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'uploads')
app.config['DATABASE_FOLDER'] = os.path.join(app.root_path, '..', 'DatabaseStorage')
print(app.config['UPLOAD_FOLDER'])
print(app.config['DATABASE_FOLDER'])
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATABASE_FOLDER'], exist_ok=True)
initialize_db(app)
initialize_ecpm(app)
limiter = Limiter(
    get_remote_address,
    app = app,
    default_limits = ["3000 per hour"], # ~ 1/second
    storage_uri = "memory://", # redis or monogo for production...
    default_limits_exempt_when = lambda: isDeveloper(
        session.get("username", None),
        app.debug
    )
)

# [PRE-REQUEST] always have user "logged in" (generate temp accounts)
@app.before_request
def verify_auth():
    path = request.path

    # Skip static files (CSS, JS, images, texts)
    if path.startswith('/static/'):
        return

    # Skip S2S (Unity Ads servers)
    if path.startswith('/S2S') or path.startswith('/Fake/S2S'):
        return

    # Skip Identity (Identity must decide whether to create temp user)
    if path.startswith('/Identity'):
        return

    user_agent = request.headers.get("User-Agent", "")
    if user_agent == "Unity":
        # For Unity, we rely on /Identity to establish the session.
        # If the cookie is missing/invalid, Unity should call Identity() again.
        return
   
    # If session already has a valid user, keep it
    username = session.get("username")
    if username and fetch_user(username) is not None:
        return

    if path.startswith('/SID'):
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
        cashouts = [],
        created_at = time.time()
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
    print("=== /Identity CALLED ===")
    print("COOKIES:", request.cookies)
    print("SESSION BEFORE:", dict(session))

    username = session.get("username")
    user = fetch_user(username) if username else None

    # No session → create temp user
    if user is None:
        generate_temp_user()
        username = session.get("username")
        print("NEW TEMP USER CREATED BY /Identity:", username)
        print("SESSION AFTER:", dict(session))
        return username

    print("EXISTING USER:", username)
    return user["username"]


# ask server for SID (document ID)
@app.route("/SID")
@none_required
def SID(user):
    print("=== /SID CALLED ===")
    print("REQUEST HEADERS:", dict(request.headers))
    print("SESSION:", dict(session))
    print("USER:", user)
    print("COOKIES:", request.cookies)
    print("SECRET KEY:", app.secret_key)
    if not user:
        return "-1"
    return str(user.doc_id)


# debugger view (veiw/create users)
@app.route('/')
@none_required
def index(user):
    if user and isDeveloper(user["username"], debug=app.debug):
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
    # 4 values for wallet_status
    ageEnabled = get_age_restriction_enabled()
    minAge = get_minimum_age()
    userAge = get_user_age()
    hideAll = get_hide_all_buttons()


# eCPM values
    interstitial_ecpm = get_recent_ecpm("interstitial") or 0.0  # e.g. $1.20
    rewarded_ecpm = get_recent_ecpm("rewarded") or 0.0     # e.g. $10.00

    # Total ads watched
    total_ads = sum(
    u.get("interstitial", 0) + u.get("rewarded", 0)
    for u in users
)

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
        #values for included dasboard.html from walle_status
        enabled=ageEnabled,
        min_age=minAge,
        user_age=userAge,
        hide_all=hideAll,

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




# route to fetch a list of all users
@app.route('/api/users', methods=['GET'])
@admin_required
def GetAllUsers(user):
    users = fetch_users()
    for u in users:
        u["earnings"] = f"${u.get('earnings', 0.0):0.5f}"
        u["total_cashout"] = f"${u.get('total_cashout', 0.0):0.2f}"
        u["created_at"] = convert_epoch(u.get("created_at", 0))
        u["sid"] = u.doc_id
    response = make_response(jsonify(users))
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


# Create a new account for Unity
@app.route('/Register', methods=['POST'])
@app.route('/CreateUser', methods=['POST'])
def CreateUser():
    # validate form
    if "" in request.form.values():
        return "Error: Please Fill All Fields!"

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    # validate username
    if len(username) < 1 or len(username) > 36:
        return "Error: Username must be 1-36 characters long"
    if fetch_user(username) is not None:
        return "Error: Username is taken"
    if not username.isalnum():
        return "Error: Username must be alphanumeric"

    # validate email
    if fetch_user_email(email) is not None:
        return "Error: Email already registered to an account"

    # validate password
    if len(password) < 8:
        return "Error: Password must be at least 8 characters long"

    # Normal registration
    new_user = create_user(
        username=username,
        email=email,
        password=bcrypt.generate_password_hash(password).decode('utf-8'),
        gems=0,
        bonus=0,
        rewarded=0,
        interstitial=0,
        children=[]
    )

    if not new_user:
        return "Error: Could not create user"

    session["username"] = new_user["username"]
    return "User has been created!"

#----claim temp user after registretion (after/createUser)
def is_guid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


@app.route('/ClaimTempAccount', methods=['POST'])
@none_required
def ClaimTempAccount(user):
    # Only temp users can be claimed
    if not user or not is_guid(user["username"]):
        return "Error: No temp account to claim"

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    # Validate username/email/password (same as CreateUser)
    if fetch_user(username) is not None:
        return "Error: Username is taken"
    if fetch_user_email(email) is not None:
        return "Error: Email already registered"
    if len(password) < 8:
        return "Error: Password must be at least 8 characters long"

    # Update the temp user into a real user
    success = update_user(
        user["username"],
        username=username,
        email=email,
        password=bcrypt.generate_password_hash(password).decode('utf-8'),
    )

    if not success:
        return "Error: Could not claim temp account"

    session["username"] = username
    return "Temp account claimed successfully!"


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
@limiter.limit("2/second", exempt_when=lambda: isDeveloper(
    session.get("username", None),
    app.debug
))
def GetGem(user):
    user["gems"] += int(request.form["gems"])
    update_user(user["username"], gems=user["gems"])
    session["gems"] = user["gems"]
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"

#--SyncGems--
@app.route("/SyncGems", methods=["POST"])
@none_required
def sync_gems(user):
    if not user:
        return "-1"

    # Gems earned this run
    gems_earned = int(request.form.get("gems", 0))

    # Add to lifetime total
    new_total = user.get("gems", 0) + gems_earned

    # Update DB
    update_user(user["username"], gems=new_total)

    # Update session
    session["gems"] = new_total
    return str(new_total)


# watch bonus ad (rewarded ad) worth 50 gems
@app.route('/GetBonus', methods=['POST'])
@none_required
def GetBonusGem(user):
    user["bonus"] += int(request.form["gems"])
    update_user(user["username"], bonus=user["bonus"])
    session["bonus"] = user["bonus"]
    if user['bonus'] == 1:
        return f"{user['bonus']} Bonus Gem"
    else:
        return f"{user['bonus']} Bonus Gems"
   
    # Decrement ad count ("redeem" ads by deleting them)
    user["interstitial"] -= interstitial_used
    user["rewarded"] -= rewarded_used
    success = update_user(["username"], **user)

    # done!
    return True, user


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

#--------------/CASHOUT--------------------------------
@app.route('/Cashout', methods=['POST'])
@limiter.limit("1/day", exempt_when=lambda: isDeveloper(
    session.get("username", None),
    app.debug
))
@email_required
def Cashout(user):
    print("CASHOUT ROUTE HIT")
    print("CASHOUT FUNCTION EXECUTED")
    try:
        print("USER OBJECT:", user)

        # ---------------------------------------------------------
        # 1. Must be logged in with an email
        # ---------------------------------------------------------
        email = user.get("email", None)
        if email is None:
            return jsonify({
                "success": False,
                "message": "To cashout, login or register with an email associated with a PayPal account."
            })
            print("USER OBJECT:", user)


        # ---------------------------------------------------------
        # 2. Parse gemCount safely
        # ---------------------------------------------------------
        try:
            gemCount = int(request.form["gems"])
            print("FORM DATA:", request.form)
            print("GEM COUNT RECEIVED:", gemCount)

        except Exception:
            return jsonify({
                "success": False,
                "message": "Error: Invalid gem count provided to server."
            })

        # ---------------------------------------------------------
        # 3. gemCount must be > 0
        # ---------------------------------------------------------
        if gemCount <= 0:
            return jsonify({
                "success": False,
                "message": "Input the number of gems you would like to cashout."
            })

        # Precompute totals
        baseGem = user.get("gems", 0)
        bonusGem = user.get("bonus", 0)
        totalGem = baseGem + bonusGem

        # ---------------------------------------------------------
        # 4. User must have enough gems (base + bonus)
        # ---------------------------------------------------------
        if gemCount > totalGem:
            return jsonify({
                "success": False,
                "message": f"Error: Cannot cashout {gemCount:,} gems, you only have {totalGem:,}."
            })

        # ---------------------------------------------------------
        # 5. gemCount must not exceed gemMaximum (GamerScore > 1)
        # ---------------------------------------------------------
        gemMaximum = (user["interstitial"] * 5) + (user["rewarded"] * 50)
        if gemCount > gemMaximum:
            return jsonify({
                "success": False,
                "message": (
                    f"You cannot redeem {gemCount:,} gems because your ads only justify "
                    f"{gemMaximum:,} gems. (GamerScore would exceed 1.0)"
                )
            })

        # ---------------------------------------------------------
        # 6. User must have enough ads to justify gems
        #    (same logic as minimal_ad_count)
        # ---------------------------------------------------------
        rewarded_used, interstitial_used = calculations.minimal_ad_count(
            r=user["rewarded"],
            i=user["interstitial"],
            gems=gemCount
        )
        if rewarded_used is None:
            return jsonify({
                "success": False,
                "message": (
                    f"You do not have enough rewarded/interstitial ads to justify "
                    f"{gemCount:,} gems."
                )
            })

        # ---------------------------------------------------------
        # 7. S2S earnings must be above minimum threshold
        # ---------------------------------------------------------
        MIN_EARNINGS = 0.50
        if user["earnings"] < MIN_EARNINGS:
            return jsonify({
                "success": False,
                "message": (
                    f"Your Unity ad earnings (${user['earnings']:.2f}) are too low to cash out. "
                    f"Keep playing to increase your S2S revenue."
                )
            })

        # ---------------------------------------------------------
        # 8. Minimum gemCount required
        # ---------------------------------------------------------
        MIN_GEMS = 3000
        if gemCount < MIN_GEMS:
            return jsonify({
                "success": False,
                "message": f"Minimum cashout is {MIN_GEMS:,} gems."
            })

        # ---------------------------------------------------------
        # 9. Calculate payout (same as PreviewCashout)
        # ---------------------------------------------------------
        PlayerCut, EntitledCut, AdminCut = calculations.CalculatePayoutSkill(user, gemCount)

        # ---------------------------------------------------------
        # 10. PlayerCut must exceed PayPal fee threshold
        # ---------------------------------------------------------
        if PlayerCut <= 0.25:
            return jsonify({
                "success": False,
                "message": (
                    f"Your payout (${PlayerCut:.2f}) is too small to cover PayPal's $0.25 fee."
                )
            })

        # ---------------------------------------------------------
        # 11. EntitledCut must be positive
        # ---------------------------------------------------------
        if EntitledCut <= 0:
            gemsNeeded = calculations.CalculateGemsNeeded(user, gemCount)
            return jsonify({
                "success": False,
                "message": (
                    f"Processing fees outweigh your cashout. "
                    f"You need {gemsNeeded} gems to cashout at today's rate."
                )
            })

        # ---------------------------------------------------------
        # 12. Mark ads as redeemed (S2S callbacks / anti-fraud)
        # ---------------------------------------------------------
        redeem_success, user = calculations.redeem_ads(user["username"], gemCount)
        if not redeem_success:
            return jsonify({
                "success": False,
                "message": "Ad revenue is still processing, please try again in a few hours."
            })

        # ---------------------------------------------------------
        # 13. Decrement gems (consume bonus if necessary)
        # ---------------------------------------------------------
        redeem_success, user = calculations.redeem_gems(user["username"], gemCount)
        if not redeem_success:
            return jsonify({
                "success": False,
                "message": "Insufficient gems? Gem count has de-synced?"
            })

        # ---------------------------------------------------------
        # 14. Process payout (PayPal)
        # ---------------------------------------------------------
        paypal_mode = get_paypal_mode()
        create_payout(email, EntitledCut, mode=paypal_mode)

        # ---------------------------------------------------------
        # 15. Log cashout & update earnings in DB
        # ---------------------------------------------------------
        cashout_success, user = log_cashout(
            user["username"],
            gemCount,
            PlayerCut,   # total revenue attributed to player
            EntitledCut,
            AdminCut
        )

        return jsonify({
            "success": True,
            "message": f"Cashout of ${EntitledCut:0.2f} successfully sent to {email}",  
        })

    except Exception as e:
        print("CASHOUT ERROR:", e)
        traceback.print_exc()
        # user may not be defined if error happened early
        return jsonify({
            "success": False,
            "message": "Server error",
            "user": user if 'user' in locals() else None
        }), 500
#------------END OF /CASHOUT--------------

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
    update_user(user["username"], gems=user["gems"])
    session["gems"] = user["gems"]
    return redirect("/")


# TESTING PURPOSES ONLY, Increment Gems
@app.route('/get_bonus_gem/<int:amount>')
@admin_required
def get_bonus_gem(amount, user):
    user["bonus"] += amount
    update_user(user["username"], bonus=user["bonus"])
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

#----- /login for website----------------
# take over temp_user account
# admin only login for website, NOT unity
@app.route('/Login', methods=['POST'])
@none_required
def login(user):
    oldUser = user
    newUser = fetch_user(request.form['username'])

    # verify user
    if newUser == None:
        return "User Does not Exist"
    
    # verify password
    if not bcrypt.check_password_hash(newUser['password'], request.form['password']):
        return "Password is Incorrect"

    # ADMIN-ONLY LOGIN CHECK (must be inside the function!)
    if not isDeveloper(newUser["username"], False):
        # massage your login route does this for non‑admins
        # if registered non-admin tries to login
        # "status": 403 admin required
        return "Access denied — access only for admins"

    # if old user is TEMPORARY ACCOUNT with GEMS
    oldGems = oldUser.get("gems",0) + oldUser.get("bonus",0)
    if oldUser.get("email",None) == None and oldGems > 0:
        adopt_user(parent=newUser, child=oldUser)

    # log user in  
    session["username"] = newUser["username"]
    session["gems"] = newUser["gems"]

    # redirect admins to dashboard
    if isDeveloper(newUser["username"], app.debug) and isBrowser(request):
        return redirect("/Dashboard")
    else:
        return "Logged in Successfully"

  #----- /UnityLogin for unity----------------      
@app.route('/UnityLogin', methods=['POST'])
@none_required
def unity_login(user):
    oldUser = user
    newUser = fetch_user(request.form['username'])

    # verify user
    if newUser == None:
        return "User Does not Exist"
    
    # verify password
    if not bcrypt.check_password_hash(newUser['password'], request.form['password']):
        return "Password is Incorrect"

    # TEMP ACCOUNT TAKEOVER (same as old logic)
    oldGems = oldUser.get("gems",0) + oldUser.get("bonus",0)
    if oldUser.get("email",None) == None and oldGems > 0:
        adopt_user(parent=newUser, child=oldUser)

    # log user in  
    session["username"] = newUser["username"]
    session["gems"] = newUser["gems"]

    return "Logged in Successfully"
    #------END OF /UnityLogin-----------

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