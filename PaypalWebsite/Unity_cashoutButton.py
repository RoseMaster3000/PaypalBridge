from flask import Flask, jsonify, render_template, request
from PaypalWebsite.website import app
from PaypalWebsite.decorators import *

# Independent Cash Out button state
CASH_OUT_BUTTON_VISIBLE = True
CASH_OUT_BUTTON_INTERACTABLE = True

@app.route('/api/cashout_status')
@no_SessionCookie
def cashout_status():
    return jsonify({
        "visible": CASH_OUT_BUTTON_VISIBLE,
        "interactable": CASH_OUT_BUTTON_INTERACTABLE
    })

@app.route('/update_cashout_status', methods=['GET', 'POST'])
def update_cashout_status():
    global CASH_OUT_BUTTON_VISIBLE, CASH_OUT_BUTTON_INTERACTABLE
    success = False

    if request.method == 'POST':
        CASH_OUT_BUTTON_VISIBLE = 'visible' in request.form
        CASH_OUT_BUTTON_INTERACTABLE = 'interactable' in request.form and CASH_OUT_BUTTON_VISIBLE
        success = True

    return render_template(
        'cashout_status.html',
        CASH_OUT_BUTTON_VISIBLE=CASH_OUT_BUTTON_VISIBLE,
        CASH_OUT_BUTTON_INTERACTABLE=CASH_OUT_BUTTON_INTERACTABLE,
        success=success
    )