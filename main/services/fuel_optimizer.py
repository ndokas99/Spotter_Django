from geopy.distance import geodesic
from main.utils.fuel_loader import load_fuel_stations


def get_cheapest_station_near(checkpoint, stations, radius=20):
    """
    Given a checkpoint and list of stations, find the cheapest station within radius.
    :param checkpoint: [lng, lat]
    :param stations: List of fuel station dicts
    :param radius: Radius in miles
    :return: Best station dict or None
    """
    candidates = []

    for station in stations:
        dist = geodesic(
            (checkpoint[1], checkpoint[0]),
            (station["lat"], station["lng"])
        ).miles

        if dist <= radius:
            station_copy = station.copy()
            station_copy["distance"] = dist
            candidates.append(station_copy)

    if not candidates:
        return None

    return min(candidates, key=lambda s: s["price"])


def plan_fuel_stops(checkpoints):
    stations = load_fuel_stations()
    fuel_stops = []

    for point in checkpoints:
        best_station = get_cheapest_station_near(point, stations)
        if best_station:
            fuel_stops.append(best_station)
        else:
            print(f"⚠️ No fuel station found near checkpoint at {point[1]}, {point[0]}")

    return fuel_stops

def compute_fuel_cost(total_miles, fuel_stops, miles_per_gallon=10, tank_range_miles=500):
    """
    Given total miles and chosen fuel stops, compute the total fuel cost.
    :param tank_range_miles: capacity of tank
    :param miles_per_gallon: miles travelled per gallon
    :param total_miles: Total distance of route in miles
    :param fuel_stops: List of stations (in order)
    :return: (cost: float, breakdown: list of (gallons, price, cost))
    """
    gallons_needed = total_miles / miles_per_gallon
    gallons_remaining = gallons_needed - (tank_range_miles / miles_per_gallon)  # first tank
    breakdown = []
    total_cost = 0.0

    for stop in fuel_stops:
        if gallons_remaining <= 0:
            break

        gallons_to_fill = min(tank_range_miles / miles_per_gallon, gallons_remaining)
        price_per_gallon = stop["price"]
        cost = gallons_to_fill * price_per_gallon

        breakdown.append({
            "station": stop["station_name"],
            "location": (stop["lat"], stop["lng"]),
            "gallons": round(gallons_to_fill, 2),
            "price": price_per_gallon,
            "cost": round(cost, 2)
        })

        total_cost += cost
        gallons_remaining -= gallons_to_fill

    return round(total_cost, 2), breakdown
