# rate_limit.py
import time
from flask import jsonify
from PaypalWebsite.isDevelopers import isDeveloper


#cooldown_seconds determins limit 24*60*60 is 1 day limit
# #in seconds
def check_cashout_rate_limit(user, cooldown_seconds=24*60*60):
    username = user.get("username")

    # ⭐ ADMIN BYPASS
    if isDeveloper(username):
        return None  # Admins skip rate limit entirely

    now = int(time.time())
    last = user.get("last_cashout_time", 0)

    if now - last < cooldown_seconds:
        remaining = cooldown_seconds - (now - last)
        return jsonify({
            "success": False,
            "rate_limited": True,
            "remaining_seconds": remaining,
            "message": "You can only cash out once per day."
        }), 429

    return None