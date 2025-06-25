import time
import requests
from django.conf import settings
from geopy.distance import geodesic
from openrouteservice import convert


ORS_ROUTE_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
GEOCODE_URL = "https://api.geoapify.com/v1/batch/geocode/search"
API_KEY = settings.GEOAPIFY_API_KEY

TIMEOUT = 1.5
MAX_ATTEMPTS = 15

def get_coordinates(start, end):
    url = f"{GEOCODE_URL}?apiKey={API_KEY}"

    response = requests.post(url, json=[start, end])
    if response.status_code != 202:
        raise Exception(f"Failed to create Geoapify batch job: {response.text}")

    job_id = response.json()["id"]
    results_url = f"{url}&id={job_id}"

    time.sleep(TIMEOUT)
    for attempt in range(MAX_ATTEMPTS):
        resp = requests.get(results_url)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 202:
            #print(f"Still processing... (Attempt {attempt + 1})")
            time.sleep(TIMEOUT)
        else:
            raise Exception(f"Error while polling: {resp.status_code} - {resp.text}")

    raise TimeoutError("Geoapify batch job did not complete in time.")

def get_route(start, end):
    """
    Get route coordinates from start to end
    :param start: staring location
    :param end: ending location
    :return: get route and distance
    """
    headers = {
        'Accept': 'application/geo+json',
        'Authorization': settings.ORS_API_KEY,
        'Content-Type': 'application/json; charset=utf-8'
    }

    start, end = get_coordinates(start, end)

    body = {
        "coordinates": [
            [start.get('lon'), start.get('lat')],
            [end.get('lon'), end.get('lat')]
        ]
    }

    response = requests.post(ORS_ROUTE_URL, headers=headers, json=body)
    response.raise_for_status()

    data = response.json()

    geometry = convert.decode_polyline(data['routes'][0]['geometry'])['coordinates']
    distance_m = data['routes'][0]['summary']['distance']
    distance_miles = distance_m / 1609.34

    return {
        "geometry": geometry,
        "distance_miles": distance_miles
    }

def get_fuel_checkpoints(geometry, max_range_miles=500):
    """
    Splits a route geometry into checkpoints spaced by the vehicle range.
    :param geometry: List of [lng, lat] route coordinates (as from ORS)
    :param max_range_miles: Max distance vehicle can drive on a full tank
    :return: List of [lng, lat] coordinates where fuel stops should occur
    """
    checkpoints = []
    distance_since_last_stop = 0.0

    for i in range(1, len(geometry)):
        prev = geometry[i - 1]
        curr = geometry[i]

        segment_distance = geodesic((prev[1], prev[0]), (curr[1], curr[0])).miles
        distance_since_last_stop += segment_distance

        if distance_since_last_stop >= max_range_miles:
            checkpoints.append(curr)
            distance_since_last_stop = 0.0

    return checkpoints