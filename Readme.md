## About
Unity Game & Flask Server that work together to allow players to earn real money. Its uses Unity S2S Callbacks to record validated ads to a private database. The server can then allow users to cash out their ad revenue using Paypal API.


## Authorizations
For paypal to send out Payouts, your business account needs to be approved [here](https://www.paypal.com/payoutsweb/landing) (Payouts API [cost](https://www.paypal.com/us/business/paypal-business-fees#statement-10) 2% internationally and $0.25 domestically.) Also, to verify ad consumption, your Unity account will need approved for S2S callbacks [here](https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks#Implementation).

## Cashout Idea
When a user watches an ad, Unity has a webhook (S2S) which verifies the ad as has been consumed. When this happens, we could also use Unity Advertising Statistics API to record the eCPM at the time. This essentially allows us to calculate the revenue that single ad generated. Then, when a user goes to cashout, we can aggregate the total revenue they have generated. We can then calculate how many gems they have collected VS how many gems we have probably spawned for them (based on the ads they have watched) and then give them a proportionate claim to their ad revenue. Naturally, we skim some percentage off the top for ourselves (~30%?)


## Links
* [Server Code Repo](https://github.com/RoseMaster3000/PaypalBridge)
* [Unity Game Repo](https://github.com/dima02021988/ZigZag-racing-3D)
* [Roadmap Document (Google Doc)](https://docs.google.com/document/d/1l3iB7BCuJ02Ti9mMHsHlRsdQ069UTaXS7fMQZbOZelc/edit?usp=sharing)
* [Production Server (PythonAnywhere)](https://dcherevatsky.pythonanywhere.com)


### Dependencies
* [Paypal API](https://developer.paypal.com/braintree/docs/guides/paypal/server-side/python/)
* [Flask Docs](https://flask.palletsprojects.com/en/stable/)
* [Unity S2S](https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks)
* [Unity Ad Statistics (for CPM)](https://docs.unity3d.com/Packages/com.unity.ads@3.2/manual/AdvertisingResourcesStats.html)

## Secrets
API keys/sensitive data are included in a file called `SECRET.py`. This file must be manually transferred, as it is ignored from the git repository.