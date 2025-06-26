# wallet_Button.py
from flask import Flask, jsonify, render_template, request
from PaypalWebsite.website import app, bcrypt
from PaypalWebsite.decorators import *

# line only needed if standalon webapp, starting app like main.py
# app = Flask(__name__)  

# Default button states
WALLET_BUTTON_VISIBLE = True
WALLET_BUTTON_INTERACTABLE = True

@app.route('/api/wallet_status')
@no_SessionCookie
def wallet_status():
    # This route is completely stateless—no session, no cookies
    interactable = WALLET_BUTTON_INTERACTABLE if WALLET_BUTTON_VISIBLE else False
    return jsonify({
        "visible": WALLET_BUTTON_VISIBLE,
        "interactable": interactable
    })

@app.route('/update_wallet_status', methods=['GET', 'POST'])
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
    # line only needed if standalon webapp, starting app like main.py
'''if __name__ == "__main__":  
    app.run(debug=True)'''

