import math
import requests
from django.conf import settings


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculates the great-circle distance between two GPS coordinates
    using the Haversine formula
    """
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def eta_label(distance_km: float, mode: str = "driving") -> str:
    """
    Returns a human-readable ETA string for the UI.
    """
    speed_kmh = 25 if mode == "driving" else 5
    minutes = max(3, round((distance_km / speed_kmh) * 60))
    if mode == "driving":
        return f"~{minutes} min by moto"
    return f"~{minutes} min on foot"


def get_osrm_transit(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    mode: str = "driving",
) -> dict:
    """
    Calls the OSRM routing engine to get a real transit time estimate
    """
    osrm_profile = "driving" if mode == "driving" else "foot"
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/{osrm_profile}/"
        f"{from_lng},{from_lat};{to_lng},{to_lat}"
        f"?overview=false&steps=false"
    )

    try:
        response = requests.get(url, timeout=4)
        response.raise_for_status()
        data = response.json()
        route = data["routes"][0]
        duration_seconds = int(route["duration"])
        distance_km = round(route["distance"] / 1000, 2)
        minutes = max(3, round(duration_seconds / 60))
        label = (
            f"~{minutes} min by moto" if mode == "driving"
            else f"~{minutes} min on foot"
        )
        return {
            "mode": mode,
            "duration_seconds": duration_seconds,
            "duration_label": label,
            "distance_km": distance_km,
        }
    except Exception:
        # OSRM unreachable, fall back to Haversine estimate
        distance_km = haversine_km(from_lat, from_lng, to_lat, to_lng)
        speed_kmh = 25 if mode == "driving" else 5
        duration_seconds = int((distance_km / speed_kmh) * 3600)
        return {
            "mode": mode,
            "duration_seconds": duration_seconds,
            "duration_label": eta_label(distance_km, mode),
            "distance_km": distance_km,
        }
