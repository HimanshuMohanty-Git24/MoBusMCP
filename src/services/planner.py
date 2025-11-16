"""
Journey planning and route finding service
Uses JSON database for all operations
"""
from typing import List, Dict, Optional
from ..data import ROUTES, STOPS, get_routes_for_stop

def find_routes(from_location: str, to_location: str) -> List[Dict]:
    """
    Find all routes connecting two locations
    
    Args:
        from_location: Starting location name
        to_location: Destination location name
    
    Returns:
        List of routes with journey details
    """
    from_location_lower = from_location.lower()
    to_location_lower = to_location.lower()
    
    matching_routes = []
    
    for route_num, route_data in ROUTES.items():
        stops = [stop.lower() for stop in route_data.get('stops', [])]
        
        # Find if both locations are in this route
        from_idx = -1
        to_idx = -1
        
        for idx, stop in enumerate(stops):
            if from_location_lower in stop:
                from_idx = idx
            if to_location_lower in stop:
                to_idx = idx
        
        # Check if route connects both locations
        if from_idx >= 0 and to_idx >= 0 and from_idx < to_idx:
            matching_routes.append({
                'route_number': route_num,
                'route_name': route_data.get('route_name', ''),
                'from_stop': route_data['stops'][from_idx],
                'to_stop': route_data['stops'][to_idx],
                'stops_between': to_idx - from_idx,
                'all_stops': route_data['stops'][from_idx:to_idx+1],
                'distance_km': route_data.get('distance_km', 0),
                'via': route_data.get('via', '')
            })
    
    # Sort by number of stops (fewer is better)
    matching_routes.sort(key=lambda x: x['stops_between'])
    
    return matching_routes

def plan_journey(start: str, end: str, preferences: Optional[Dict] = None) -> Dict:
    """
    Plan a complete journey with possible transfers
    
    Args:
        start: Starting location name
        end: Destination location name
        preferences: User preferences (minimize_transfers, prefer_ac, etc.)
    
    Returns:
        Complete journey plan with routes, transfers, and timing
    """
    if preferences is None:
        preferences = {}
    
    # Find direct routes first
    direct_routes = find_routes(start, end)
    
    if direct_routes:
        best_route = direct_routes[0]
        return {
            'journey_type': 'direct',
            'total_routes': 1,
            'total_transfers': 0,
            'estimated_time_minutes': best_route['stops_between'] * 3,  # ~3 min per stop
            'recommended_route': {
                'route_number': best_route['route_number'],
                'route_name': best_route['route_name'],
                'from_stop': best_route['from_stop'],
                'to_stop': best_route['to_stop'],
                'stops_count': best_route['stops_between'] + 1,
                'stops': best_route['all_stops']
            }
        }
    
    # No direct route - find routes with one transfer
    start_routes = get_routes_for_stop(start)
    end_routes = get_routes_for_stop(end)
    
    transfer_options = []
    
    for start_route in start_routes:
        for end_route in end_routes:
            # Find common stops (potential transfer points)
            start_stops = [s.lower() for s in start_route['stops']]
            end_stops = [s.lower() for s in end_route['stops']]
            
            common_stops = set(start_stops) & set(end_stops)
            
            if common_stops:
                for transfer_stop in common_stops:
                    transfer_options.append({
                        'first_route': {
                            'route_number': start_route['route_number'],
                            'route_name': start_route['route_name'],
                            'from': start,
                            'to': transfer_stop
                        },
                        'transfer_point': transfer_stop,
                        'second_route': {
                            'route_number': end_route['route_number'],
                            'route_name': end_route['route_name'],
                            'from': transfer_stop,
                            'to': end
                        }
                    })
    
    if transfer_options:
        return {
            'journey_type': 'with_transfer',
            'total_routes': 2,
            'total_transfers': 1,
            'estimated_time_minutes': 45,  # Estimate with transfer
            'transfer_options': transfer_options[:3]  # Top 3 options
        }
    
    # No routes found
    return {
        'journey_type': 'no_route_found',
        'message': f'No direct or connecting routes found between {start} and {end}',
        'suggestion': 'Try searching for nearby bus stops or alternative locations'
    }

def get_route_stops(route_number: str) -> List[str]:
    """Get all stops for a route in order"""
    route_data = ROUTES.get(route_number, {})
    return route_data.get('stops', [])

def is_stop_on_route(stop_name: str, route_number: str) -> bool:
    """Check if a stop is on a specific route"""
    stops = get_route_stops(route_number)
    stop_name_lower = stop_name.lower()
    return any(stop_name_lower in stop.lower() for stop in stops)
