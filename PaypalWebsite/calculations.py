from flask import jsonify, request
from PaypalWebsite.decorators import none_required
from PaypalWebsite.ecpm import get_recent_ecpm

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
    from PaypalWebsite.database.tinydb import fetch_user
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
    from PaypalWebsite.database.tinydb import fetch_user, update_user
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
        update_user(**user)
        return True, user
    else:
        return False, user

    #------------END OF CALCULATIONS------------------   

#-------------restrictions to the calculation--------------

def register_payout_routes(app):
    @app.route('/PreviewCashout', methods=['POST'])
    @none_required
    def PreviewCashoutPost(user):
        data = {
            "gemCount": 0,
            "baseGem": user.get("gems", 0),
            "bonusGem": user.get("bonus", 0),
            "totalGem": user.get("gems", 0) + user.get("bonus", 0),
            "payout": "$0.00",
            "message": "..."
        }

        # ---------------------------------------------------------
        # 1. Must be logged in
        # ---------------------------------------------------------
        if user.get("email", None) is None:
            data["gemCount"] = -2
            data["message"] = "To cashout, login or register with an email associated with a PayPal account."
            return jsonify(data)

        # ---------------------------------------------------------
        # 2. Parse gemCount safely
        # ---------------------------------------------------------
        try:
            data["gemCount"] = int(request.form["gems"])
        except:
            data["gemCount"] = -3
            data["message"] = "Error: Invalid gem count provided to server."
            return jsonify(data)

        gemCount = data["gemCount"]

        # ---------------------------------------------------------
        # 3. gemCount must be > 0
        # ---------------------------------------------------------
        if gemCount <= 0:
            data["gemCount"] = -3
            data["message"] = "Input the number of gems you would like to cashout."
            return jsonify(data)

        # ---------------------------------------------------------
        # 4. User must have enough gems
        # ---------------------------------------------------------
        if gemCount > data["totalGem"]:
            data["message"] = f"Error: Cannot cashout {gemCount:,} gems, you only have {data['totalGem']:,}."
            return jsonify(data)

        # ---------------------------------------------------------
        # 5. gemCount must not exceed gemMaximum (GamerScore > 1)
        # ---------------------------------------------------------
        gemMaximum = (user["interstitial"] * 5) + (user["rewarded"] * 50)
        if gemCount > gemMaximum:
            data["message"] = (
                f"You cannot redeem {gemCount:,} gems because your ads only justify "
                f"{gemMaximum:,} gems. (GamerScore would exceed 1.0)"
            )
            return jsonify(data)

        # ---------------------------------------------------------
        # 6. User must have enough ads to justify gems
        # ---------------------------------------------------------
        rewarded_used, interstitial_used = minimal_ad_count(
            r=user["rewarded"],
            i=user["interstitial"],
            gems=gemCount
        )
        if rewarded_used is None:
            data["message"] = (
                f"You do not have enough rewarded/interstitial ads to justify "
                f"{gemCount:,} gems."
            )
            return jsonify(data)

        # ---------------------------------------------------------
        # 7. S2S earnings must be above minimum threshold
        # ---------------------------------------------------------
        MIN_EARNINGS = 0.50
        if user["earnings"] < MIN_EARNINGS:
            data["message"] = (
                f"Your Unity ad earnings (${user['earnings']:.2f}) are too low to cash out. "
                f"Keep playing to increase your S2S revenue."
            )
            return jsonify(data)

        # ---------------------------------------------------------
        # 8. Minimum gemCount required
        # ---------------------------------------------------------
        MIN_GEMS = 3000
        if gemCount < MIN_GEMS:
            data["message"] = f"Minimum cashout is {MIN_GEMS:,} gems."
            return jsonify(data)

        # ---------------------------------------------------------
        # 9. Calculate payout
        # ---------------------------------------------------------
        PlayerCut, EntitledCut, AdminCut = CalculatePayoutSkill(user, gemCount)
        data["payout"] = f"${EntitledCut:,.02f}"

        # ---------------------------------------------------------
        # 10. PlayerCut must exceed PayPal fee
        # ---------------------------------------------------------
        if PlayerCut <= 0.25:
            data["message"] = (
                f"Your payout (${PlayerCut:.2f}) is too small to cover PayPal's $0.25 fee."
            )
            data["payout"] = "$0.00"
            return jsonify(data)

        # ---------------------------------------------------------
        # 11. EntitledCut must be positive
        # ---------------------------------------------------------
        if EntitledCut <= 0:
            gemsNeeded = CalculateGemsNeeded(user, gemCount)
            data["message"] = (
                f"Processing fees outweigh your cashout. "
                f"You need {gemsNeeded} gems to cashout at today's rate."
            )
            data["payout"] = "$0.00"
            return jsonify(data)

        # ---------------------------------------------------------
        # 12. SUCCESS — valid cashout preview
        # ---------------------------------------------------------
        data["message"] = (
            f"A {gemCount:,} gem cashout would result in a ${EntitledCut:,.02f} payout to PayPal!"
        )

        return jsonify(data)

    #---------------END RESTRICTIONS-------------------