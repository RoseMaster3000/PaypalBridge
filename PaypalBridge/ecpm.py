from PaypalBridge.SECRET import UNITY_MONETIZATION_KEY, UNITY_ORGINIZATION_KEY
import requests
import json
from os.path import isfile
import datetime
from datetime import timezone, timedelta

# check if timestamp is from last 24 hours...
def is_recent(timestamp_str, hours=24):
    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    now = datetime.datetime.now(timezone.utc)
    time_diff = now - timestamp
    return time_diff < timedelta(hours=hours)

# get ecpm from yesterday (cached in "ecpm.json")
def get_recent_ecpm(placement):
    ecpmFile = "ecpm.json"

    # get eCPM file from cached file (if it exists)
    if not isfile(ecpmFile):
        data = save_ecpm(resolution="day", dayRange=1, output=ecpmFile)
    else:
        with open(ecpmFile, 'r') as file:
            data = json.loads(file.read())
        # verify cached eCPM file has recent infor
        if not is_recent(data[0]["timestamp"]):
            data = save_ecpm(resolution="day", dayRange=1, output=ecpmFile)

    # return data
    return extract(data, placement)

# extract ecpm for specifc placement type from UnityAdPlacment api data
def extract(data, placement):
    placement = placement.lower()
    for item in data:
        if placement in item["placement"].lower():
            return item["ecpm"]
    return 0
 
# Fetch the eCPM average from yesterday - today
# resolution : hour, day, week, month, year, all
# dayRange   : how many days from today in past to query
def get_ecpm(resolution="week", dayRange=1):
    base_url = f"https://monetization.api.unity.com/stats/v1/operate/organizations/{UNITY_ORGINIZATION_KEY}"

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=dayRange)

    params = {
        "fields": "adrequest_count,start_count,view_count,available_sum,revenue_sum",
        "scale": resolution,
        "groupBy": "placement",
        "start": yesterday.isoformat(),
        "end": today.isoformat()
    }

    headers = {
        "Authorization": f"Token {UNITY_MONETIZATION_KEY}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        newdata = []
        for r in data:
            if r["placement"] != None:
                newrecord = {}
                newrecord["placement"] = r["placement"]
                newrecord["timestamp"] = r["timestamp"]
                newrecord["fill_rate"] = r["start_count"] / r["adrequest_count"] if r["adrequest_count"] else 0
                newrecord["completion_rate"] = r["view_count"] / r["start_count"] if r["start_count"] else 0
                newrecord["ecpm"] = r["revenue_sum"] / r["view_count"] if r["view_count"] else 0 
                newrecord["ecpm"] *= 1000
                newdata.append(newrecord)
        return newdata 

    except requests.exceptions.RequestException as e:
        print(f"Error querying Unity Ads API: {e}")
        if response is not None:
            print(f"Response code: {response.status_code}")
            try:
                print(response.json())
            except json.JSONDecodeError:
                print(response.text)
        return None

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(response.text)
        return None

# save ecpm to file
def save_ecpm(resolution, dayRange, output):
    data = get_ecpm(resolution, dayRange)
    with open(output, 'w') as file:
        json.dump(data, file, indent=4)
    return data


def test():
    #save_ecpm(resolution='day', dayRange=1, output="ecpm.json")
    print(get_recent_ecpm("rewarded"))
