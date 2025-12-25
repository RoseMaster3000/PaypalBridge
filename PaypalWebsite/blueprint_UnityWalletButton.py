# wallet_Button.py
from flask import Blueprint, jsonify, render_template, request
from PaypalWebsite.decorators import *

wallet_button = Blueprint("wallet_button", __name__)

# Default button global states
WALLET_BUTTON_VISIBLE = True
WALLET_BUTTON_INTERACTABLE = True

@wallet_button.route('/api/wallet_status')
def wallet_status():
    # This route is completely stateless—no session, no cookies
    interactable = WALLET_BUTTON_INTERACTABLE if WALLET_BUTTON_VISIBLE else False
    return jsonify({
        "visible": WALLET_BUTTON_VISIBLE,
        "interactable": interactable
    })

@wallet_button.route('/update_wallet_status', methods=['GET', 'POST'])
def update_wallet_status():
    global WALLET_BUTTON_VISIBLE, WALLET_BUTTON_INTERACTABLE
    success = False

    if request.method == 'POST':
        WALLET_BUTTON_VISIBLE = 'visible' in request.form
        WALLET_BUTTON_INTERACTABLE = 'interactable' in request.form and WALLET_BUTTON_VISIBLE
        success = True

    return render_template(
        'wallet_status.html',
        WALLET_BUTTON_VISIBLE=WALLET_BUTTON_VISIBLE,
        WALLET_BUTTON_INTERACTABLE=WALLET_BUTTON_INTERACTABLE,
        success=success
    )
    


