import os
import csv
import time
import requests
from django.conf import settings


ORIGINAL_FILE = os.path.join(settings.BASE_DIR, 'main', 'data', 'fuel-prices-for-be-assessment.csv')
GEOCODED_FILE = os.path.join(settings.BASE_DIR, 'main', 'data', 'fuel_prices_geocoded.csv')
ERRORS = os.path.join(settings.BASE_DIR, 'main', 'data', 'errors.csv')

BATCH_ENDPOINT = "https://api.geoapify.com/v1/batch/geocode/search"
API_KEY = settings.GEOAPIFY_API_KEY

# Job polling settings
TIMEOUT = 3             # seconds between polling attempts
MAX_ATTEMPTS = 50       # number of polling attempts per batch

_FUEL_STATIONS = None   # In-memory cache

def geocode_batch_geoapify(addresses):
    """Submits a batch geocoding job and polls for the result."""
    url = f"{BATCH_ENDPOINT}?apiKey={API_KEY}"

    response = requests.post(url, json=addresses)
    if response.status_code != 202:
        raise Exception(f"Failed to create Geoapify batch job: {response.text}")

    job_id = response.json()["id"]
    results_url = f"{url}&id={job_id}"
    print(f"Batch job submitted (ID: {job_id}). Waiting for results...")

    time.sleep(TIMEOUT)
    for attempt in range(MAX_ATTEMPTS):
        resp = requests.get(results_url)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 202:
            print(f"Still processing... (Attempt {attempt + 1})")
            time.sleep(TIMEOUT)
        else:
            raise Exception(f"Error while polling: {resp.status_code} - {resp.text}")


    raise TimeoutError("Geoapify batch job did not complete in time.")


def geocode_fuel_prices_bulk():
    """Processes the original CSV and writes a geocoded version with lat/lon."""
    with open(ORIGINAL_FILE, 'r', newline='', encoding='utf-8') as infile:
        all_rows = list(csv.DictReader(infile))

    batch_size = 19
    fieldnames = all_rows[0].keys() | {'latitude', 'longitude'}

    with (open(GEOCODED_FILE, 'w', newline='', encoding='utf-8') as outfile, open(ERRORS, 'w', newline='', encoding='utf-8') as errorfile):
        writer, errorWriter = csv.DictWriter(outfile, fieldnames=fieldnames), csv.DictWriter(errorfile, fieldnames=all_rows[0].keys())
        writer.writeheader()
        errorWriter.writeheader()

        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i + batch_size]
            print(f"Processing batch {i} to {i + len(batch)}...")

            addresses = []
            for row in batch:
                parts = [row.get('Address', '').strip(), row.get('City', '').strip(), row.get('State', '').strip(), 'USA']
                full_address = ', '.join(p for p in parts if p)
                addresses.append(full_address)

            try:
                results = geocode_batch_geoapify(addresses)
                for row, result in zip(batch, results):
                    if result.get("lat") and result.get("lon"):
                        row['latitude'], row['longitude'] = result['lat'], result['lon']
                    else:
                        row['latitude'], row['longitude'] = '', ''
                        print(f"Failed to geocode: {row.get('address')}")
                    writer.writerow(row)
            except Exception as e:
                print(f"Error during batch geocoding: {e}")
                for row in batch:
                    errorWriter.writerow(row)

            time.sleep(1.1)


def load_fuel_stations():
    """Load geocoded fuel stations into memory."""
    global _FUEL_STATIONS
    if _FUEL_STATIONS is not None:
        return _FUEL_STATIONS

    if not os.path.exists(GEOCODED_FILE):
        print("Geocoded file not found. Starting geocoding...")
        geocode_fuel_prices_bulk()

    with open(GEOCODED_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        _FUEL_STATIONS = [
            {
                'Truckstop Name': row.get('Truckstop Name'),
                'lat': float(row['latitude']),
                'lng': float(row['longitude']),
                'price': float(row.get('Retail Price', 0))
            }
            for row in reader if row.get('latitude') and row.get('longitude')
        ]

    return _FUEL_STATIONS