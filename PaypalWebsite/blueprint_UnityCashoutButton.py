from flask import Blueprint, jsonify, render_template, request, redirect
from PaypalWebsite.decorators import *
from PaypalWebsite.database.tinydb import set_override_status, get_override_status

# blueprint
cashout_button = Blueprint("cashout_button", __name__)


# Local-only flags (not stored)

CASH_OUT_BUTTON_INTERACTABLE = True

@cashout_button.route('/api/cashout_status')
def cashout_status():
    override = get_override_status()
    return jsonify({
        "interactable": CASH_OUT_BUTTON_INTERACTABLE,
        "override": override
    })

@cashout_button.route('/update_cashout_status', methods=['GET', 'POST'])
def update_cashout_status():
    global CASH_OUT_BUTTON_INTERACTABLE
    success = False

    if request.method == 'POST':
        CASH_OUT_BUTTON_INTERACTABLE = 'interactable' in request.form
        override = CASH_OUT_BUTTON_INTERACTABLE

        set_override_status(override)
        success = True
        return redirect('/update_cashout_status?success=1')

    override = get_override_status()
    return render_template(
        'cashout_status.html',
        CASH_OUT_OVERRIDE_ENABLED=override,
        success=request.args.get('success') == '1'
    )