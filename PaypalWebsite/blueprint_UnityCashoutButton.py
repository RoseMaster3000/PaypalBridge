from flask import Blueprint, jsonify, render_template, request, redirect, session
from PaypalWebsite.decorators import *
from PaypalWebsite.database.tinydb import (
    set_override_status,
    get_override_status,
    set_admin_interactable_status,
    get_admin_interactable_status
)
from PaypalWebsite.isDevelopers import isDeveloper

cashout_button = Blueprint("cashout_button", __name__)

@cashout_button.route('/api/cashout_status')
def cashout_status():
    override = get_override_status()
    adminInteractable = get_admin_interactable_status()

    # Determine if current user is admin
    username = session.get("username", None)
    is_admin = isDeveloper(username, debug=False)

    # Determine mode
    if not override:
        mode = "normal"
    else:
        if not adminInteractable:
            mode = "maintenance_all"
        else:
            mode = "admin_only"

    return jsonify({
        "override": override,
        "adminInteractable": adminInteractable,
        "is_admin": is_admin,
        "mode": mode
    })


@cashout_button.route('/update_cashout_status', methods=['GET', 'POST'])
def update_cashout_status():
    if request.method == 'POST':
        override = 'override' in request.form
        adminInteractable = 'adminInteractable' in request.form

        set_override_status(override)
        set_admin_interactable_status(adminInteractable)

        return redirect('/update_cashout_status?success=1')

    override = get_override_status()
    adminInteractable = get_admin_interactable_status()

    return render_template(
        'cashout_status.html',
        override=override,
        adminInteractable=adminInteractable,
        success=request.args.get('success') == '1'
    )