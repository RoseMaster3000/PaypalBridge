# https://github.com/paypal/paypal-rest-api-specifications
# https://developer.paypal.com/docs/api/payments.payouts-batch/v1/
from PaypalWebsite.SECRET import (
    SANDBOX_PAYPAL_CLIENT_ID, SANDBOX_PAYPAL_SECRET,
    LIVE_PAYPAL_CLIENT_ID, LIVE_PAYPAL_SECRET
)
from PaypalWebsite.database.tinydb import log, get_paypal_mode
from uuid import uuid4
import requests
import base64
import re

def is_valid_paypal_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Convert ClientID/Secret -> OAUTH token
def get_access_token(mode=None):
    # Use manual override if provided, otherwise use TinyDB
    mode = mode or get_paypal_mode()
    if mode == 'sandbox':
        client_id = SANDBOX_PAYPAL_CLIENT_ID
        secret = SANDBOX_PAYPAL_SECRET
        base_url = 'https://api-m.sandbox.paypal.com'
    else:
        client_id = LIVE_PAYPAL_CLIENT_ID
        secret = LIVE_PAYPAL_SECRET
        base_url = 'https://api-m.paypal.com'

    auth_string = f"{client_id}:{secret}"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {encoded_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    response = requests.post(
        f'{base_url}/v1/oauth2/token',
        headers=headers,
        data=data
    )
    if response.ok:
        return response.json()['access_token'], base_url
    else:
        raise Exception(f"PayPal token request failed: {response.status_code} - {response.text}")

# Send money to PayPal email
def create_payout(recipient_email, amount, mode=None):

    # Validate email
    if not is_valid_paypal_email(recipient_email):
        raise Exception(f"Invalid PayPal email format: {recipient_email}")

    # Use manual override if provided, otherwise use TinyDB
    mode = mode or get_paypal_mode()
    try:
        access_token, base_url = get_access_token(mode)
    except Exception:
        import time
        time.sleep(1)
        access_token, base_url = get_access_token(mode)


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
        id=payment_id,
        receiver=recipient_email,
        value=f"{amount:0.2f}",
        currency="USD"
    )

    # submit payout to PayPal
    response = requests.post(
        f'{base_url}/v1/payments/payouts',
        headers=headers,
        json=payload
    )
    if response.ok:
        result = response.json()
        status = result["batch_header"]["batch_status"]

        if status not in ("SUCCESS", "PENDING"):
            raise Exception(f"PayPal payout failed with status: {status}")

        return result
    else:
        raise Exception(f"Payout failed: {response.status_code} - {response.text}")

# Optional test
def test_payout():
    confirmation = create_payout("sb-sbjc037505269@personal.example.com", 5.50, mode='sandbox')
    from pprint import pprint
    pprint(confirmation)