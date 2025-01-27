## About
Unity game & Flask server that work togetehr to allow players to earn real money. Its uses Unity S2S Callbacks to record validated ads to a private database. The server can then allow users to cash out their ad revenue using Paypal API.


## Links
* [Server Code Repo](https://github.com/RoseMaster3000/PaypalBridge)
* [Unity Game Repo](https://github.com/dima02021988/ZigZag-racing-3D)
* [Roadmap Document (Google Doc)](https://docs.google.com/document/d/1l3iB7BCuJ02Ti9mMHsHlRsdQ069UTaXS7fMQZbOZelc/edit?usp=sharing)
* [Production Server (PythonAnywhere)](https://dcherevatsky.pythonanywhere.com)


### Replit (expired)
* [Development Server: Replit](https://a793bff8-567d-48ec-8cb5-8559e412c1fd-00-38j54p3698xo4.janeway.replit.dev/)
* [Replit Editor](https://a793bff8-567d-48ec-8cb5-8559e412c1fd-00-38j54p3698xo4.janeway.replit.dev/)


### Dependencies
* [Paypal API](https://developer.paypal.com/braintree/docs/guides/paypal/server-side/python/)
* [Flask](https://flask.palletsprojects.com/en/stable/)
* [Unity S2S](https://docs.unity.com/ads/en-us/manual/ImplementingS2SRedeemCallbacks)


## Secrets
API keys/sensitive data are included in a file called `SECRET.py`. This file must be manually transferred, as it is ignored from the git repository.