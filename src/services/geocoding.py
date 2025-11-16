"""
Enhanced Geocoding Service
Uses BOTH SerpAPI (Google Maps) and OpenStreetMap Nominatim for accurate location finding
Falls back between services for maximum reliability
"""
import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

class MultiSourceGeocoder:
    """Intelligent geocoder using SerpAPI and OSM Nominatim with fallback"""
    
    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY', os.getenv('SERP_API_KEY'))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MoBusApp/1.0 (Bus Route Planner)'
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Rate limiting
    
    def _rate_limit(self):
        """Ensure we don't exceed API rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def geocode_with_serpapi(self, address: str, city: str = "Bhubaneswar") -> Optional[Dict]:
        """
        Geocode using SerpAPI Google Maps Places API
        
        Args:
            address: Address or location name
            city: City name
        
        Returns:
            Dictionary with lat, lon, name, address or None
        """
        if not self.serpapi_key:
            return None
        
        self._rate_limit()
        
        # Build search query
        query = f"{address}, {city}, Odisha, India"
        
        params = {
            'engine': 'google_maps',
            'q': query,
            'type': 'search',
            'api_key': self.serpapi_key
        }
        
        try:
            response = self.session.get(
                'https://serpapi.com/search',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            local_results = data.get('local_results', [])
            
            if local_results:
                result = local_results[0]
                gps = result.get('gps_coordinates', {})
                
                if gps:
                    return {
                        'lat': gps.get('latitude'),
                        'lon': gps.get('longitude'),
                        'name': result.get('title', ''),
                        'address': result.get('address', ''),
                        'type': result.get('type', ''),
                        'rating': result.get('rating'),
                        'place_id': result.get('place_id', ''),
                        'source': 'google_maps_serpapi',
                        'confidence': 'high'
                    }
        except Exception as e:
            print(f"SerpAPI geocoding error: {e}")
        
        return None
    
    def geocode_with_osm(self, address: str, city: str = "Bhubaneswar") -> Optional[Dict]:
        """
        Geocode using OpenStreetMap Nominatim API
        
        Args:
            address: Address or location name
            city: City name
        
        Returns:
            Dictionary with lat, lon, display_name or None
        """
        self._rate_limit()
        
        # Build search query
        query = f"{address}, {city}, Odisha, India"
        
        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        try:
            response = self.session.get(
                'https://nominatim.openstreetmap.org/search',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            if results:
                result = results[0]
                return {
                    'lat': float(result['lat']),
                    'lon': float(result['lon']),
                    'name': result.get('display_name', ''),
                    'address': result.get('display_name', ''),
                    'type': result.get('type', ''),
                    'importance': float(result.get('importance', 0)),
                    'source': 'openstreetmap',
                    'confidence': 'medium'
                }
        except Exception as e:
            print(f"OSM geocoding error: {e}")
        
        return None
    
    def geocode(self, address: str, city: str = "Bhubaneswar") -> Optional[Dict]:
        """
        Intelligent geocoding with multi-source fallback
        Tries SerpAPI first (more accurate), falls back to OSM
        
        Args:
            address: Address or location name
            city: City name
        
        Returns:
            Best geocoding result or None
        """
        # Try SerpAPI first (Google Maps - most accurate)
        result = self.geocode_with_serpapi(address, city)
        if result:
            return result
        
        # Fallback to OSM Nominatim (free, reliable)
        result = self.geocode_with_osm(address, city)
        if result:
            return result
        
        return None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Reverse geocode coordinates to address
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Dictionary with address details or None
        """
        self._rate_limit()
        
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1
        }
        
        try:
            response = self.session.get(
                'https://nominatim.openstreetmap.org/reverse',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
        
        return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

def find_nearest_stops(
    lat: float, 
    lon: float, 
    stops_data: Dict,
    max_results: int = 5,
    max_distance_km: float = 2.0
) -> List[Dict]:
    """
    Find nearest bus stops to a coordinate
    
    Args:
        lat: Latitude
        lon: Longitude
        stops_data: Dictionary of stops from database
        max_results: Maximum number of stops to return
        max_distance_km: Maximum distance to search (km)
    
    Returns:
        List of nearest stops with distance info
    """
    user_location = (lat, lon)
    nearest_stops = []
    
    for stop_id, stop_info in stops_data.items():
        stop_coords = stop_info.get('coordinates')
        if not stop_coords:
            continue
        
        stop_lat = stop_coords.get('lat')
        stop_lon = stop_coords.get('lon')
        if not stop_lat or not stop_lon:
            continue
        
        distance_km = calculate_distance(lat, lon, stop_lat, stop_lon)
        
        if distance_km <= max_distance_km:
            nearest_stops.append({
                'stop_id': stop_id,
                'stop_name': stop_info.get('name', ''),
                'city': stop_info.get('city', ''),
                'distance_km': round(distance_km, 2),
                'distance_m': round(distance_km * 1000),
                'walking_time_min': round(distance_km * 12),  # ~12 min per km walking
                'coordinates': stop_coords
            })
    
    # Sort by distance
    nearest_stops.sort(key=lambda x: x['distance_km'])
    
    return nearest_stops[:max_results]

# Global geocoder instance
_geocoder = MultiSourceGeocoder()

def get_coordinates(location: str, city: str = "Bhubaneswar") -> Dict[str, float]:
    """
    Get coordinates for a location (backward compatible)
    
    Args:
        location: Location name
    
    Returns:
        Dictionary with lat and lon keys
    """
    result = _geocoder.geocode(location, city)
    if result:
        return {'lat': result['lat'], 'lon': result['lon']}
    
    # Fallback to default (Bhubaneswar center)
    return {'lat': 20.2961, 'lon': 85.8245}

def get_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points (backward compatible)"""
    return calculate_distance(lat1, lon1, lat2, lon2)

def geocode_location(location: str, city: str = "Bhubaneswar") -> Optional[Dict]:
    """Geocode a location (backward compatible)"""
    return _geocoder.geocode(location, city)

def reverse_geocode_location(lat: float, lon: float) -> Optional[Dict]:
    """Reverse geocode coordinates (backward compatible)"""
    return _geocoder.reverse_geocode(lat, lon)

def calculate_distance_between_locations(loc1: str, loc2: str) -> float:
    """Calculate distance between two named locations"""
    coords1 = get_coordinates(loc1)
    coords2 = get_coordinates(loc2)
    
    return calculate_distance(coords1['lat'], coords1['lon'], coords2['lat'], coords2['lon'])
