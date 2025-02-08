# from PaypalBridge.paypal import test_payout
# test_payout()


from PaypalBridge.website import minimal_ad_count

# 1 intersitial == 1 gem (red)
# 1 rewarded == 10 gems  (green)
# assert 0, 10 == minimal_ad_count(10,10,101)
# assert 10, 1 == minimal_ad_count(10,1,20)
# assert None, None == minimal_ad_count(10,1,21)
# assert None, None == minimal_ad_count(9,1,20)
# assert 0, 2 = minimal_ad_count(0,2,15)


print(minimal_ad_count(10,10,101))
print(minimal_ad_count(10,1,20))
print(minimal_ad_count(10,1,21))
print(minimal_ad_count(9,1,20))
print(minimal_ad_count(0,2,15))