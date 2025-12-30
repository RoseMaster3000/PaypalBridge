from flask import Blueprint, jsonify, render_template, request, redirect
from PaypalWebsite.decorators import *
from PaypalWebsite.database.tinydb import (
    set_override_status,
    get_override_status,
    set_interactable_status,
    get_interactable_status
)
# blueprint
cashout_button = Blueprint("cashout_button", __name__)


@cashout_button.route('/api/cashout_status')
def cashout_status():
    override = get_override_status()
    interactable = get_interactable_status()
    return jsonify({
        "override": override,
        "interactable": interactable
    })

@cashout_button.route('/update_cashout_status', methods=['GET', 'POST'])
def update_cashout_status():
    success = False

    if request.method == 'POST':
        override = 'override' in request.form
        interactable = 'interactable' in request.form

        set_override_status(override)
        set_interactable_status(interactable)
        success = True
        return redirect('/update_cashout_status?success=1')

    override = get_override_status()
    interactable = get_interactable_status()

    return render_template(
        'cashout_status.html',
        cashoutOverride=override,
        override=override,
        interactable=interactable,
        success=request.args.get('success') == '1'
)

