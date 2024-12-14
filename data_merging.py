import json
import math
import requests

def fetch_json(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

fetch_stop_journey_time_cache = {}

def fetch_stop_journey_time(stop_id):
    if "normal" in fetch_stop_journey_time_cache:
        return fetch_stop_journey_time_cache["normal"].get(stop_id, {})
    url = f"https://timeinterval.hkbuseta.com/times/all.json"
    try:
        data = fetch_json(url)
        fetch_stop_journey_time_cache["normal"] = data
        return data.get(stop_id, {})  # Return only the relevant stop data
    except requests.RequestException as error:
        print(f"Error fetching data for stop {stop_id}: {error}")
        return {}  # Return an empty object if there's an error

def fetch_stop_journey_time_hourly(stop_id, weekday, hour):
    if f"{weekday}/{hour}" in fetch_stop_journey_time_cache:
        return fetch_stop_journey_time_cache[f"{weekday}/{hour}"].get(stop_id, {})
    url = f"https://timeinterval.hkbuseta.com/times_hourly/{weekday}/{hour}/all.json"
    try:
        data = fetch_json(url)
        fetch_stop_journey_time_cache[f"{weekday}/{hour}"] = data
        return data.get(stop_id, {})  # Return only the relevant stop data
    except requests.RequestException as error:
        print(f"Error fetching data for stop {stop_id}: {error}")
        return {}  # Return an empty object if there's an error

def haversine(lat1, lon1, lat2, lon2):
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371.0 * c

data_sheet = fetch_json("https://data.hkbus.app/routeFareList.min.json")
route_list = data_sheet["routeList"]
stop_list = data_sheet["stopList"]

normalized_route_list = {}
normalized_stop_list = {}
stop_journey_times = {}

for route_key, route_data in route_list.items():
    if len(route_data["stops"]) > 0 and any(len(stops) > 0 for co, stops in route_data["stops"].items()):
        normalized_route_list[route_key] = {
            "route": route_data["route"],
            "co": route_data["co"],
            "stops": route_data["stops"]
        }
        for co, stops in route_data["stops"].items():
            for stop in stops:
                if stop not in normalized_stop_list:
                    normalized_stop_list[stop] = stop_list[stop]
                    normalized_stop_list[stop]["co"] = [co]
                elif co not in normalized_stop_list[stop]["co"]:
                    normalized_stop_list[stop]["co"].append(co)
            for index, stop in enumerate(stops[:-1]):
                next_stop = stops[index + 1]
                if stop not in stop_journey_times:
                    stop_journey_times[stop] = {}
                journey_time = stop_journey_times[stop]
                journey_time_fetch_normal = fetch_stop_journey_time(stop)
                if next_stop in journey_time_fetch_normal:
                    time = round(journey_time_fetch_normal[next_stop], 2)
                    if next_stop not in journey_time:
                        journey_time[next_stop] = {"normal": time}
                    elif "normal" not in journey_time[next_stop] or journey_time[next_stop]["normal"] > time:
                        journey_time[next_stop]["normal"] = time
                for weekday in range(7):
                    for hour in range(24):
                        hour_str = f"{hour:02d}"
                        journey_time_fetch_hour = fetch_stop_journey_time_hourly(stop, weekday, hour_str)
                        if next_stop in journey_time_fetch_hour:
                            time = round(journey_time_fetch_hour[next_stop], 2)
                            if next_stop not in journey_time:
                                journey_time[next_stop] = {weekday: {hour_str: time}}
                            elif weekday not in journey_time[next_stop]:
                                journey_time[next_stop][weekday] = {hour_str: time}
                            elif hour_str not in journey_time[next_stop][weekday] or journey_time[next_stop][weekday][hour_str] > time:
                                journey_time[next_stop][weekday][hour_str] = time

for stop_id, journey_time_data in stop_journey_times.items():
    if "normal" in journey_time_data:
        normal_time = journey_time_data["normal"]
        for weekday in range(7):
            for hour in range(24):
                hour_str = f"{hour:02d}"
                if weekday in journey_time_data and hour_str in journey_time_data[weekday]:
                    hourly_time = journey_time_data[weekday][hour_str]
                    if normal_time == hourly_time:
                        del journey_time_data[weekday][hour_str]
            if weekday in journey_time_data and len(journey_time_data[weekday]) <= 0:
                del journey_time_data[weekday]

for stop_id, stop in normalized_stop_list.items():
    stop["nearby"] = []
    lat = stop["location"]["lat"]
    lng = stop["location"]["lng"]
    for other_stop_id, other_stop in normalized_stop_list.items():
        if stop_id != other_stop_id:
            distance = haversine(lat, lng, other_stop["location"]["lat"], other_stop["location"]["lng"])
            if distance <= 0.3:
                stop["nearby"].append(other_stop_id)


result = {
    "routeList": normalized_route_list,
    "stopList": normalized_stop_list,
    "journeyTimes": stop_journey_times
}

with open('routeTimeList.json', 'w', encoding='UTF-8') as f:
    json.dump(result, f, indent=4)

with open('routeTimeList.min.json', 'w', encoding='UTF-8') as f:
    json.dump(result, f)