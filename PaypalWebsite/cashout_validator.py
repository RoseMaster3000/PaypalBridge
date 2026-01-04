from PaypalWebsite.calculations import(
    minimal_ad_count, 
    CalculatePayoutSkill, 
    CalculateGemsNeeded)

def validate_cashout(user, gemCount):
    data = {
        "success": False,
        "gemCount": gemCount,
        "baseGem": user.get("gems", 0),
        "bonusGem": user.get("bonus", 0),
        "totalGem": user.get("gems", 0) + user.get("bonus", 0),
        "payout": "$0.00",
        "message": ""
    }

    # 1. Must be logged in
    if user.get("email") is None:
        data["message"] = "To cashout, login or register with an email associated with a PayPal account."
        return data

    # 2. gemCount must be > 0
    if gemCount <= 0:
        data["message"] = "Input the number of gems you would like to cashout."
        return data

    # 3. User must have enough gems
    if gemCount > data["totalGem"]:
        data["message"] = f"Error: Cannot cashout {gemCount:,} gems, you only have {data['totalGem']:,}."
        return data

    # 4. gemCount must not exceed gemMaximum
    gemMaximum = (user["interstitial"] * 5) + (user["rewarded"] * 50)
    if gemCount > gemMaximum:
        data["message"] = (
            f"You cannot redeem {gemCount:,} gems because your ads only justify "
            f"{gemMaximum:,} gems. (GamerScore would exceed 1.0)"
        )
        return data

    # 5. User must have enough ads to justify gems
    rewarded_used, interstitial_used = minimal_ad_count(
        r=user["rewarded"],
        i=user["interstitial"],
        gems=gemCount
    )
    if rewarded_used is None:
        data["message"] = (
            f"You do not have enough rewarded/interstitial ads to justify "
            f"{gemCount:,} gems."
        )
        return data

    # 6. S2S earnings must be above minimum threshold
    MIN_EARNINGS = 0.50
    if user["earnings"] < MIN_EARNINGS:
        data["message"] = (
            f"Your Unity ad earnings (${user['earnings']:.2f}) are too low to cash out. "
            f"Keep playing to increase your S2S revenue."
        )
        return data

    
    # 7. Dynamic minimum gems required
    dynamic_min = CalculateGemsNeeded(user, 0)
    if gemCount < dynamic_min:
        data["message"] = f"Minimum cashout is {dynamic_min:,} gems at today's rate."
        return data

    # 8. Calculate payout
    PlayerCut, EntitledCut, AdminCut = CalculatePayoutSkill(user, gemCount)
    data["payout"] = f"${EntitledCut:,.02f}"

    # 9. PlayerCut must exceed PayPal fee
    if PlayerCut <= 0.25:
        data["message"] = (
            f"Your payout (${PlayerCut:.2f}) is too small to cover PayPal's $0.25 fee."
        )
        data["payout"] = "$0.00"
        return data

    # 10. EntitledCut must be positive
    if EntitledCut <= 0:
        gemsNeeded = CalculateGemsNeeded(user, gemCount)
        data["message"] = (
            f"Processing fees outweigh your cashout. "
            f"You need {gemsNeeded:,} gems to cashout at today's rate."
        )
        data["payout"] = "$0.00"
        return data

    # SUCCESS
    data["success"] = True
    data["message"] = (
        f"A {gemCount:,} gem cashout would result in a ${EntitledCut:,.02f} payout to PayPal!"
    )
    return data