from flask import jsonify, request
from PaypalWebsite.decorators import none_required
from PaypalWebsite.ecpm import get_recent_ecpm
from PaypalWebsite.database.tinydb import update_user, fetch_user
#from PaypalWebsite.cashout_validator import validate_cashout


# Calculate USD payed (based on hardcoded value for ads)
# (OLD method where rewarded/intersitial ads have FIXED values)
"""def CalculatePayoutFixed(gemCount):
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
    return CalculateCuts(TotalRevenue)"""

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
def redeem_ads(username, gemCount):
    #from PaypalWebsite.database.tinydb import fetch_user
    user = fetch_user(username)

    # Calculate minimal ad count needed to redeem gems
    rewarded_used, interstitial_used = minimal_ad_count(
        i = user["interstitial"],
        r = user["rewarded"],
        gems = gemCount
    )

        # Not enough ads → fail
    if rewarded_used is None:
        return False, user
    # Enough ads → success
    return True, user

# decrment base gems (then bonus gems if necessary)
# return T/F if not enough gems
def redeem_gems(username, gemCount):
    #from PaypalWebsite.database.tinydb import fetch_user, update_user
    user = fetch_user(username)

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
        update_user(
            user["username"],
            gems=user["gems"],
            bonus=user["bonus"]
        )
        return True, user
    else:
        return False, user

    #------------END OF CALCULATIONS------------------   

#-------------restrictions to the calculation--/preview---------


    #---------------END RESTRICTIONS-------------------

    @app.route('/AddBonus', methods=['POST'])
    @none_required
    def AddBonus(user):
        user = fetch_user(user["username"])

        # Real S2S flag from Unity
        is_s2s = request.form.get("s2s", "0") == "1"

        # Debug mode flag (server controlled)
        # CHANGE TO FALSE FOR PRODUCTION
        DEBUG_MODE = True 

        # -----------------------------------------
        # REAL S2S PATH ( is_s2s="1")
        # -----------------------------------------
        if is_s2s:
            user["bonus"] += 50
            update_user(user["username"], bonus=user["bonus"])
            return jsonify({"bonusGem": user["bonus"], "mode": "s2s"})

        # -----------------------------------------
        # DEBUG PATH (debug=true)
        # -----------------------------------------
        if DEBUG_MODE:
            user["bonus"] += 50
            update_user(user["username"], bonus=user["bonus"])
            return jsonify({"bonusGem": user["bonus"], "mode": "debug"})

        # -----------------------------------------
        # PRODUCTION (no debug=false, no S2S="0")
        # -----------------------------------------
        return jsonify({"error": "Bonus not allowed"}), 403