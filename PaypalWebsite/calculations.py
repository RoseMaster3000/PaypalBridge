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

#TotalRevenue = totalEarnings
# so  totalEarnings is split 70/30
def CalculateCuts(TotalRevenue):
    PlayerShare = 0.70  # percent the user gets
    AdminCut = TotalRevenue * 0.30  # your 30% BEFORE fee

    PlayerCut = TotalRevenue * PlayerShare

    # PayPal fee comes from the player's 70%
    if (PlayerCut * 0.02 > 0.25):
        PaypalProcessingFee = PlayerCut * 0.02  # 2% domestic
    else:
        PaypalProcessingFee = 0.25  # 25¢ international

    EntitledCut = PlayerCut - PaypalProcessingFee

    # rounding
    PlayerCut = round(PlayerCut, 2)
    EntitledCut = round(EntitledCut, 2)
    AdminCut = round(AdminCut, 2)



    return PlayerCut, EntitledCut, AdminCut




# Calculate # of gems needed to make at least 1 cent
# (First use user's earnings / gems, then see how many more gems they would need)
# (will add "~" symbol need additional theoretical market value gems)
def CalculateGemsNeeded(user, gemCount):
    gemsLeft = max(user["gems"] - gemCount, 0)
    gemsNeeded = gemCount
    totalEarnings = CalulateEarnings(user, gemCount)
    entitledCut = 0
    singleGemValue = MarketGemValue()
    fakeGemsUsed = 0

    while entitledCut < 0.01:
        # Use real gems first
        if gemsLeft > 0:
            gemsNeeded += 1
            gemsLeft -= 1
            totalEarnings = CalulateEarnings(user, gemsNeeded)
        # Use theoretical gems
        else:
            gemsNeeded += 1
            fakeGemsUsed += 1
            totalEarnings += singleGemValue

        _, entitledCut, _ = CalculateCuts(totalEarnings)

        # Safety cap to prevent infinite loop
        if gemsNeeded > 999999:
            print("WARNING: CalculateGemsNeeded exceeded safe bounds")
            return 999999

    print(f"Calculated minimum gems needed: {gemsNeeded} (includes {fakeGemsUsed} fake gems)")
    return gemsNeeded



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

        # Not enough ads  fail
    if rewarded_used is None:
        return False, user
    # Enough ads  success
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

    #---------------END RESTRICTIONS-------------------

    