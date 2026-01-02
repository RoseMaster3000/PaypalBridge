from flask import Blueprint, jsonify, render_template, request
from PaypalWebsite.database.tinydb import (
    get_age_restriction_enabled,
    get_minimum_age,
    get_user_age,
    set_age_restriction_enabled,
    set_minimum_age,
    set_user_age,
    

)

wallet_button = Blueprint("wallet_button", __name__)

#---flask API to communicate with Unity----
@wallet_button.route('/api/wallet_status')
def wallet_status():
    # Load settings from TinyDB
    enabled = get_age_restriction_enabled()
    min_age = get_minimum_age()
    user_age = get_user_age()
    

    # Determine if user is underage
    underage = enabled and user_age < min_age

    # Unity will use this to hide buttons
    return jsonify({
        "age_restriction_enabled": enabled,
        "minimum_age": min_age,
        "user_age": user_age,
        "underage": underage
        
    })

#---flask API(we control) to communicate with website (wallet_status.html)----
@wallet_button.route('/update_wallet_status', methods=['GET', 'POST'])
def update_wallet_status():
    if request.method == 'POST':
        set_age_restriction_enabled('enabled' in request.form)
        set_minimum_age(int(request.form.get('min_age', 10)))
        set_user_age(int(request.form.get('user_age', 18)))
        

    return render_template(
        'wallet_status.html',
        age_restriction_enabled=get_age_restriction_enabled(),
        min_age=get_minimum_age(),
        user_age=get_user_age() 
    )