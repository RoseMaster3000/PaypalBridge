from flask import Blueprint, render_template, request
from datetime import datetime
from PaypalWebsite.decorators import admin_required
from PaypalWebsite.database.tinydb import fetch_users, convert_epoch
from PaypalWebsite.ecpm import get_recent_ecpm

web_cashoutHistory = Blueprint("web_cashoutHistory", __name__)

def fetch_user_by_sid(sid):
    users = fetch_users()
    for u in users:
        if u.doc_id == sid:
            return u
    return None

@web_cashoutHistory.route("/CashoutHistoryView/<int:sid>")
@admin_required
def CashoutHistoryView(user, sid):
    targetUser = fetch_user_by_sid(sid)
    if not targetUser:
        return f"User with SID {sid} not found", 404

    # Parse filters
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    exact_str = request.args.get("exact")

    start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
    end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None
    exact_date = datetime.strptime(exact_str, "%Y-%m-%d") if exact_str else None

    filtered_cashouts = []
    for c in targetUser["cashouts"]:
        c["time"] = convert_epoch(c["time"])
        try:
            t = datetime.strptime(c["time"], "%m/%d/%Y %H:%M:%S")
        except:
            continue

        # Apply filters
        if exact_date:
            if t.date() != exact_date.date():
                continue
        else:
            if start_date and t < start_date:
                continue
            if end_date and t > end_date:
                continue

        # Developer profit per cashout
        c["PaypalFee"] = round(c.get("PaypalFee", c["TotalPayout"] - c["UserPayout"]), 2)
        c["RealProfit"] = round(c.get("RealProfit", c["AdminPayout"]), 2)
        filtered_cashouts.append(c)

    # Ad metrics
    interstitial_ecpm = get_recent_ecpm("interstitial")
    rewarded_ecpm = get_recent_ecpm("rewarded")

    interstitial_value = interstitial_ecpm / 1000
    rewarded_value = rewarded_ecpm / 1000

    total_interstitial = targetUser["interstitial"]
    total_rewarded = targetUser["rewarded"]
    total_ads = total_interstitial + total_rewarded

    interstitial_revenue = total_interstitial * interstitial_value
    rewarded_revenue = total_rewarded * rewarded_value
    total_ad_revenue = interstitial_revenue + rewarded_revenue

    total_redeemed_gems = sum(c["gems"] for c in filtered_cashouts)
    total_profit = sum(c["RealProfit"] for c in filtered_cashouts)

    targetUser["cashouts"] = filtered_cashouts

    return render_template(
        "cashout_history.html",
        user=targetUser,
        sid=sid,
        total_redeemed_gems=total_redeemed_gems,
        interstitialECPM=f"${interstitial_ecpm:,.2f}",
        rewardedECPM=f"${rewarded_ecpm:,.2f}",
        totalAds=total_ads,
        gemValue=f"${(interstitial_value + rewarded_value) / 55:,.5f}",
        totalAdRevenue=f"${total_ad_revenue:,.2f}",
        rewardedRevenue=f"${rewarded_revenue:,.4f}",
        interstitialRevenue=f"${interstitial_revenue:,.4f}",
        rewardedPerAd=f"${rewarded_value:,.5f}",
        interstitialPerAd=f"${interstitial_value:,.5f}",
        totalProfit=f"${total_profit:,.2f}"
    )