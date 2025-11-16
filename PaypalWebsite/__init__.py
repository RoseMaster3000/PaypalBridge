from PaypalWebsite import appad
from PaypalWebsite import Unity_WalletButton
from PaypalWebsite import Unity_cashoutButton
from PaypalWebsite import website
from PaypalWebsite.website import app

#impor/register web_cashout.py to main.py webapp starter 
from PaypalWebsite.web_cashoutHistory import web_cashoutHistory
app.register_blueprint(web_cashoutHistory)

