from flask import Flask, jsonify, render_template, request
from PaypalWebsite.website import app
from PaypalWebsite.decorators import *

# Independent Cash Out button global state
CASH_OUT_BUTTON_VISIBLE = True
CASH_OUT_BUTTON_INTERACTABLE = True
CASH_OUT_OVERRIDE_ENABLED = False # True = use walletManager gemcount logic, False = force server(web) override

@app.route('/api/cashout_status')
def cashout_status():
    return jsonify({
        "visible": CASH_OUT_BUTTON_VISIBLE,
        "interactable": CASH_OUT_BUTTON_INTERACTABLE,
        "override": CASH_OUT_OVERRIDE_ENABLED
    })

@app.route('/update_cashout_status', methods=['GET', 'POST'])
def update_cashout_status():
    global CASH_OUT_BUTTON_VISIBLE, CASH_OUT_BUTTON_INTERACTABLE, CASH_OUT_OVERRIDE_ENABLED
    success = False

    if request.method == 'POST':
        CASH_OUT_BUTTON_VISIBLE = 'visible' in request.form
        CASH_OUT_BUTTON_INTERACTABLE = 'interactable' in request.form and CASH_OUT_BUTTON_VISIBLE
        CASH_OUT_OVERRIDE_ENABLED = CASH_OUT_BUTTON_VISIBLE and CASH_OUT_BUTTON_INTERACTABLE
        success = True

    return render_template(
        'cashout_status.html',
        CASH_OUT_BUTTON_VISIBLE=CASH_OUT_BUTTON_VISIBLE,
        CASH_OUT_BUTTON_INTERACTABLE=CASH_OUT_BUTTON_INTERACTABLE,
        CASH_OUT_OVERRIDE_ENABLED=CASH_OUT_OVERRIDE_ENABLED,
        success=success
    )