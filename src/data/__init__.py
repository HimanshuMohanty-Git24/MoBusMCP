"""
Data module for Mo Bus MCP Server
Loads all bus data from JSON database
"""
import json
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load JSON database
JSON_DB_PATH = PROJECT_ROOT / "mo_bus_complete_database.json"

def load_database():
    """Load the complete Mo Bus database from JSON"""
    try:
        with open(JSON_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Database file not found at {JSON_DB_PATH}. "
            "Please ensure mo_bus_complete_database.json exists in the project root."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in database file: {e}")

# Load database on module import
_database = load_database()

# Export data structures
STOPS = _database.get('stops', {})
ROUTES = _database.get('routes', {})
FARE_STRUCTURE = _database.get('fare_structure', {})
METADATA = _database.get('metadata', {})

# Helper functions
def get_stop_info(stop_id: str) -> dict:
    """Get information about a specific stop"""
    return STOPS.get(stop_id, {})

def get_route_info(route_number: str) -> dict:
    """Get information about a specific route"""
    return ROUTES.get(route_number, {})

def search_stops(query: str) -> list:
    """Search for stops by name or city"""
    query_lower = query.lower()
    results = []
    for stop_id, stop_data in STOPS.items():
        if (query_lower in stop_data.get('name', '').lower() or 
            query_lower in stop_data.get('city', '').lower()):
            results.append({
                'id': stop_id,
                **stop_data
            })
    return results

def search_routes(query: str) -> list:
    """Search for routes by number or name"""
    query_lower = query.lower()
    results = []
    for route_num, route_data in ROUTES.items():
        if (query_lower in route_num.lower() or 
            query_lower in route_data.get('route_name', '').lower()):
            results.append({
                'route_number': route_num,
                **route_data
            })
    return results

def get_routes_for_stop(stop_name: str) -> list:
    """Get all routes that pass through a stop"""
    stop_name_lower = stop_name.lower()
    routes = []
    for route_num, route_data in ROUTES.items():
        stops = route_data.get('stops', [])
        if any(stop_name_lower in stop.lower() for stop in stops):
            routes.append({
                'route_number': route_num,
                'route_name': route_data.get('route_name', ''),
                'stops': stops
            })
    return routes

def calculate_fare(distance_km: float) -> int:
    """Calculate fare based on distance"""
    distance_slabs = FARE_STRUCTURE.get('distance_slabs', [])
    for slab in distance_slabs:
        if slab['min_km'] <= distance_km < slab['max_km']:
            return slab['fare']
    # Return max fare if distance exceeds all slabs
    return distance_slabs[-1]['fare'] if distance_slabs else 0

def _enrich_stops_with_coordinates():
    """Add approximate coordinates to stops"""
    coordinate_map = {
        'acharya_vihar_square': {'lat': 20.2943, 'lon': 85.8133},
        'kiit_square': {'lat': 20.3557, 'lon': 85.8183},
        'kiit_campus': {'lat': 20.3557, 'lon': 85.8183},
        'patia_square': {'lat': 20.3540, 'lon': 85.8205},
        'master_canteen': {'lat': 20.2697, 'lon': 85.8387},
        'ag_square': {'lat': 20.2961, 'lon': 85.8245},
        'baramunda_bsabt': {'lat': 20.2815, 'lon': 85.8038},
        'bhubaneswar_railway_station': {'lat': 20.2697, 'lon': 85.8387},
        'nandankanan': {'lat': 20.4008, 'lon': 85.8156},
        'airport': {'lat': 20.2441, 'lon': 85.8178},
        'biju_patnaik_airport': {'lat': 20.2441, 'lon': 85.8178},
        'sum_hospital': {'lat': 20.2847, 'lon': 85.7753},
        'vani_vihar_square': {'lat': 20.2972, 'lon': 85.8205},
        'jaydev_vihar_square': {'lat': 20.2944, 'lon': 85.8180},
        'aiims': {'lat': 20.3019, 'lon': 85.8181},
        'khandagiri': {'lat': 20.2545, 'lon': 85.7783},
        'puri': {'lat': 19.8135, 'lon': 85.8312},
        'cuttack': {'lat': 20.4625, 'lon': 85.8828}
    }
    
    for stop_id, coords in coordinate_map.items():
        if stop_id in STOPS:
            if 'coordinates' not in STOPS[stop_id]:
                STOPS[stop_id]['coordinates'] = coords

_enrich_stops_with_coordinates()

# Export all
__all__ = [
    'STOPS',
    'ROUTES',
    'FARE_STRUCTURE',
    'METADATA',
    'get_stop_info',
    'get_route_info',
    'search_stops',
    'search_routes',
    'get_routes_for_stop',
    'calculate_fare'
]
