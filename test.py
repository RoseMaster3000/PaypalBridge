# from PaypalBridge.paypal import test_payout
# test_payout()

from PaypalBridge.ecpm import get_recent_ecpm
i = get_recent_ecpm("interstitial")
r = get_recent_ecpm("rewarded")

print("interstitial ecpm:", i)
print("    rewarded ecpm:", r)


# from PaypalBridge.website import minimal_ad_count
# assert minimal_ad_count(r=10,i=10, gems=101)  == (10, 1)
# assert minimal_ad_count(r=1, i=10, gems=20)   == (1, 10)
# assert minimal_ad_count(r=1, i=10, gems=21)   == (None, None)
# assert minimal_ad_count(r=1, i=9, gems=20)    == (None, None)
# assert minimal_ad_count(r=2, i=0, gems=15)    == (2, 0)
# assert minimal_ad_count(r=3, i=1, gems=10000) == (None, None)
# print("All tests passed ✅")


# from PaypalBridge.database.tinydb import purge_redeemed_ads
# purge_redeemed_ads()


# from PaypalBridge.database.tinydb import record_ad_round
# from PaypalBridge.website import redeem_ads

# record_ad_round(userID=1, count=296)
# redeem_ads(userID=1, gemCount=17000)


