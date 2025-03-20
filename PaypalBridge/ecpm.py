from PaypalBridge.SECRET import UNITY_MONETIZATION_KEY, UNITY_ORGINIZATION_KEY
import requests
import json
from os.path import isfile
import datetime
import time


def now():
    return int(time.time())


# check if timestamp is from last 24 hours...
def is_recent(data, hours=24):
    for record in data:
        if "request_timestamp" in record:
            time_diff = now() - record["request_timestamp"] 
            return (time_diff < (hours*3600))
    return False

# get ecpm from yesterday (cached in "ecpm.json")
def get_recent_ecpm(placement):
    ecpmFile = "ecpm-average.json"

    # get eCPM file from cached file (if it exists)
    if not isfile(ecpmFile):
        data = save_ecpm(resolution="day", dayRange=30, output=ecpmFile, aggregate=True)
    else:
        with open(ecpmFile, 'r') as file:
            data = json.loads(file.read())

    # verify cached eCPM data is up to date
    if not is_recent(data):
        data = save_ecpm(resolution="week", dayRange=1, output=ecpmFile, aggregate=True)

    # return data
    return extract(data, placement)

# extract ecpm for specifc placement type from UnityAdPlacment api data
def extract(data, placement):
    placement = placement.lower()
    for item in data:
        if placement in item.get("placement","").lower():
            return item["ecpm"]
    return 0
 
# Fetch the eCPM average from yesterday - today
# resolution : hour, day, week, month, year, all
# dayRange   : how many days from today in past to query
def get_ecpm(resolution="week", dayRange=1, aggregate=False):
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
        if aggregate:
            data = aggregated_data(data)
            with open("ecpm-aggregate.json", 'w') as file:
                json.dump(data, file, indent=4)

        newdata = [{"request_timestamp": now()}]
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


def aggregated_data(data):
    # Initialize a dictionary to store aggregated results
    aggregated_by_placement = {}

    # Aggregate data by placement
    for item in data:
        placement = item["placement"]
        
        # If this placement doesn't exist yet, create it
        if placement not in aggregated_by_placement:
            aggregated_by_placement[placement] = {
                "placement": placement,
                "adrequest_count": 0,
                "revenue_sum": 0,
                "start_count": 0,
                "available_sum": 0,
                "view_count": 0,
                "records": 0
            }
        
        # Add this item's values to the running totals
        aggregated_by_placement[placement]["adrequest_count"] += item["adrequest_count"]
        aggregated_by_placement[placement]["revenue_sum"] += item["revenue_sum"]
        aggregated_by_placement[placement]["start_count"] += item["start_count"]
        aggregated_by_placement[placement]["available_sum"] += item["available_sum"]
        aggregated_by_placement[placement]["view_count"] += item["view_count"]
        aggregated_by_placement[placement]["timestamp"] = item["timestamp"]

        # Add this record to the array of records for this placement
        aggregated_by_placement[placement]["records"] += 1

    # Convert back to list
    return list(aggregated_by_placement.values())

# save ecpm to file
def save_ecpm(resolution, dayRange, output, aggregate=False):
    data = get_ecpm(resolution, dayRange, aggregate)
    with open(output, 'w') as file:
        json.dump(data, file, indent=4)
    return data


def test():
    #save_ecpm(resolution='day', dayRange=1, output="ecpm.json")
    print(get_recent_ecpm("rewarded"))
