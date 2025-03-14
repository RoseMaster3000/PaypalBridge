from PaypalBridge.SECRET import UNITY_MONETIZATION_KEY, UNITY_ORGINIZATION_KEY
import requests
import json
import datetime

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


def test():
    data = get_ecpm(resolution='day', dayRange=30)
    print(data)

    with open('ecpm.json', 'w') as file:
        json.dump(data, file, indent=4)