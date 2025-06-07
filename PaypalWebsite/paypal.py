# https://github.com/paypal/paypal-rest-api-specifications
# https://developer.paypal.com/docs/api/payments.payouts-batch/v1/
from PaypalWebsite.SECRET import PAYPAL_CLIENT_ID, PAYPAL_SECRET 
from PaypalWebsite.database.tinydb import log
from uuid import uuid4
import requests
import base64

sandbox = True
PAYPAL_URL = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"


# Convert ClientID/Secret -> OAUTH token
def get_access_token():
    auth_string = f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {encoded_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }    
    data = {'grant_type': 'client_credentials'}
    response = requests.post(
        f'{PAYPAL_URL}/v1/oauth2/token', 
        headers=headers, 
        data=data
    )
    return response.json()['access_token']


# Send money to PayPal email
def create_payout(recipient_email, amount):
    access_token = get_access_token()
    payment_id = str(uuid4())

    # generate payout
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {
        "sender_batch_header": {
            "sender_batch_id": payment_id,
            "email_subject": "Tap Racer3D Payout"
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": f"{amount:0.2f}",
                    "currency": "USD"
                },
                "receiver": recipient_email
            }
        ]
    }
    
    # log payout in database
    log("payouts",
        id = payment_id,
        receiver = recipient_email,
        value = f"{amount:0.2f}",
        currency = "USD"
    )

    # submit payout to PayPal
    response = requests.post(
        f'{PAYPAL_URL}/v1/payments/payouts',
        headers = headers,
        json = payload
    )
    return response.json()


def test_payout():
    confirmation = create_payout("sb-sbjc037505269@personal.example.com", 5.50)
    from pprint import pprint
    pprint(confirmation)