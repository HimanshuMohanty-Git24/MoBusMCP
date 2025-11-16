"""
Mo Bus MCP Server using FastMCP
Clean, simple server for bus route planning
"""
from fastmcp import FastMCP, Context
import json
from typing import Optional
import logging

# Configure logging
from fastmcp.utilities.logging import configure_logging, get_logger
from fastmcp.server.middleware.logging import LoggingMiddleware

# Set up comprehensive logging
configure_logging(level='DEBUG')
logger = get_logger("Mo.Bus.Server")

# Import data from JSON-based module
from .data import (
    STOPS, ROUTES, FARE_STRUCTURE, METADATA,
    get_stop_info, get_route_info, search_stops,
    search_routes, get_routes_for_stop, calculate_fare
)
from .services.planner import find_routes, plan_journey
from .services.geocoding import get_coordinates, get_distance

# Initialize FastMCP server
mcp = FastMCP("Mo Bus Route Planner")

# Add logging middleware for all MCP operations
mcp.add_middleware(LoggingMiddleware(include_payloads=True, max_payload_length=2000))

# ================== RESOURCES ==================

@mcp.resource("mobus://routes/all")
def get_all_routes() -> str:
    """Complete list of all Mo Bus routes with stops and timings"""
    return json.dumps(ROUTES, indent=2, ensure_ascii=False)

@mcp.resource("mobus://stops/all")
def get_all_stops() -> str:
    """Complete list of all bus stops across Odisha"""
    return json.dumps(STOPS, indent=2, ensure_ascii=False)

@mcp.resource("mobus://fare/structure")
def get_fare_structure() -> str:
    """Mo Bus fare calculation structure based on distance"""
    return json.dumps(FARE_STRUCTURE, indent=2, ensure_ascii=False)

@mcp.resource("mobus://system/info")
def get_system_info() -> str:
    """Mo Bus system metadata and statistics"""
    return json.dumps(METADATA, indent=2, ensure_ascii=False)

# ================== TOOLS ==================

@mcp.tool()
def search_bus_routes(query: str, ctx: Context = None) -> str:
    """
    Search for bus routes by route number or name
    
    Args:
        query: Route number or route name (e.g., '10', 'Airport', 'Puri')
    
    Returns:
        JSON string with matching routes
    """
    if ctx:
        ctx.debug(f"Searching bus routes with query: '{query}'")
    logger.debug(f"Route search initiated with query: {query}")
    
    results = search_routes(query)
    
    if ctx:
        ctx.info(f"Found {len(results)} routes matching '{query}'")
    logger.info(f"Route search completed - found {len(results)} results")
    
    response = {
        "query": query,
        "total_results": len(results),
        "routes": results[:10]
    }
    
    if ctx:
        ctx.debug(f"Returning {min(10, len(results))} routes to client")
    
    return json.dumps(response, indent=2, ensure_ascii=False)

@mcp.tool()
def search_bus_stops(query: str, ctx: Context = None) -> str:
    """
    Search for bus stops by name or city
    
    Args:
        query: Stop name or city (e.g., 'Airport', 'Bhubaneswar', 'KIIT')
    
    Returns:
        JSON string with matching stops
    """
    if ctx:
        ctx.debug(f"Searching bus stops with query: '{query}'")
    logger.debug(f"Stop search initiated with query: {query}")
    
    results = search_stops(query)
    
    if ctx:
        ctx.info(f"Found {len(results)} stops matching '{query}'")
    logger.info(f"Stop search completed - found {len(results)} results")
    
    response = {
        "query": query,
        "total_results": len(results),
        "stops": results[:20]
    }
    
    if ctx:
        ctx.debug(f"Returning {min(20, len(results))} stops to client")
    
    return json.dumps(response, indent=2, ensure_ascii=False)

@mcp.tool()
def get_route_details(route_number: str, ctx: Context = None) -> str:
    """
    Get complete details of a specific bus route
    
    Args:
        route_number: Route number (e.g., '10', 'DD1', '22B')
    
    Returns:
        JSON string with route details including all stops
    """
    if ctx:
        ctx.debug(f"Fetching details for route: {route_number}")
    logger.debug(f"Route details requested for: {route_number}")
    
    route_info = get_route_info(route_number)
    
    if not route_info:
        if ctx:
            ctx.warning(f"Route {route_number} not found")
        logger.warning(f"Route not found: {route_number}")
        return json.dumps({"error": f"Route {route_number} not found"}, indent=2)
    
    if ctx:
        ctx.info(f"Retrieved details for route {route_number} with {len(route_info.get('stops', []))} stops")
    logger.info(f"Route details retrieved - {route_number} has {len(route_info.get('stops', []))} stops")
    
    response = {
        "route_number": route_number,
        **route_info
    }
    
    if ctx:
        ctx.debug(f"Sending route details to client")
    
    return json.dumps(response, indent=2, ensure_ascii=False)

@mcp.tool()
def find_routes_between_stops(from_stop: str, to_stop: str, ctx: Context = None) -> str:
    """
    Find all possible routes between two stops/locations
    
    Args:
        from_stop: Starting stop/location name
        to_stop: Destination stop/location name
    
    Returns:
        JSON string with all connecting routes
    """
    if ctx:
        ctx.debug(f"Finding routes from '{from_stop}' to '{to_stop}'")
    logger.debug(f"Route search initiated: {from_stop} -> {to_stop}")
    
    routes = find_routes(from_stop, to_stop)
    
    if ctx:
        ctx.info(f"Found {len(routes)} possible route(s) between {from_stop} and {to_stop}")
    logger.info(f"Route planning completed - found {len(routes)} routes")
    
    response = {
        "from": from_stop,
        "to": to_stop,
        "routes_found": len(routes),
        "routes": routes
    }
    
    if ctx:
        ctx.debug(f"Returning {len(routes)} route options to client")
    
    return json.dumps(response, indent=2, ensure_ascii=False)

@mcp.tool()
def plan_bus_journey(
    start: str, 
    end: str,
    minimize_transfers: bool = True,
    prefer_ac: bool = False,
    ctx: Context = None
) -> str:
    """
    Plan a complete journey with route suggestions, transfers, and timing
    
    Args:
        start: Starting location name
        end: Destination location name
        minimize_transfers: Prefer routes with fewer transfers (default: True)
        prefer_ac: Prefer AC buses if available (default: False)
    
    Returns:
        JSON string with complete journey plan
    """
    if ctx:
        ctx.info(f"Journey planning requested: {start} -> {end}")
        ctx.debug(f"   Preferences: minimize_transfers={minimize_transfers}, prefer_ac={prefer_ac}")
    
    logger.info(f"Journey planning initiated: {start} -> {end}")
    logger.debug(f"User preferences - minimize_transfers: {minimize_transfers}, prefer_ac: {prefer_ac}")
    
    preferences = {
        "minimize_transfers": minimize_transfers,
        "prefer_ac": prefer_ac
    }
    
    if ctx:
        ctx.debug("Computing optimal journey path...")
    logger.debug("Computing journey plan...")
    
    journey_plan = plan_journey(start, end, preferences)
    
    if ctx:
        num_routes = len(journey_plan.get('routes', []))
        estimated_time = journey_plan.get('estimated_duration')
        total_fare = journey_plan.get('total_fare')
        ctx.info(f"Journey planned: {num_routes} route(s), ~{estimated_time} min, INR {total_fare}")
        ctx.debug(f"Sending complete journey plan to client")
    
    logger.info(f"Journey plan completed with {len(journey_plan.get('routes', []))} routes")
    
    return json.dumps(journey_plan, indent=2, ensure_ascii=False)

@mcp.tool()
def calculate_bus_fare(
    from_stop: Optional[str] = None,
    to_stop: Optional[str] = None,
    distance_km: Optional[float] = None,
    ctx: Context = None
) -> str:
    """
    Calculate bus fare based on distance or between two stops
    
    Args:
        from_stop: Starting stop name (optional if distance provided)
        to_stop: Destination stop name (optional if distance provided)
        distance_km: Direct distance in kilometers (optional if stops provided)
    
    Returns:
        JSON string with fare calculation
    """
    if ctx:
        ctx.debug(f"Fare calculation request: {from_stop or 'N/A'} -> {to_stop or 'N/A'} ({distance_km}km)")
    logger.debug(f"Fare calculation initiated - from: {from_stop}, to: {to_stop}, distance: {distance_km}")
    
    if distance_km is None and from_stop and to_stop:
        try:
            if ctx:
                ctx.debug(f"Calculating distance between {from_stop} and {to_stop}...")
            logger.debug(f"Calculating distance between {from_stop} and {to_stop}")
            
            coords1 = get_coordinates(from_stop)
            coords2 = get_coordinates(to_stop)
            distance_km = get_distance(
                coords1['lat'], coords1['lon'],
                coords2['lat'], coords2['lon']
            )
            
            if ctx:
                ctx.debug(f"Distance calculated: {distance_km:.2f} km")
            logger.info(f"Distance calculated: {distance_km:.2f} km")
        except Exception as e:
            if ctx:
                ctx.warning(f"Could not calculate distance: {str(e)}, using default 10km")
            logger.warning(f"Distance calculation failed: {e}, using default")
            distance_km = 10  # Default fallback
    
    fare = calculate_fare(distance_km or 0)
    
    if ctx:
        ctx.info(f"Fare calculated: INR {fare} for {distance_km}km")
        ctx.debug(f"Sending fare information to client")
    logger.info(f"Fare calculation complete - INR {fare} for {distance_km}km")
    
    response = {
        "distance_km": round(distance_km, 2) if distance_km else None,
        "fare_inr": fare,
        "from": from_stop,
        "to": to_stop
    }
    
    return json.dumps(response, indent=2)

@mcp.tool()
def get_stops_for_route(route_number: str, ctx: Context = None) -> str:
    """
    Get all stops for a specific route in order
    
    Args:
        route_number: Route number
    
    Returns:
        JSON string with ordered list of stops
    """
    if ctx:
        ctx.debug(f"Retrieving stops for route: {route_number}")
    logger.debug(f"Retrieving stops for route: {route_number}")
    
    route_info = get_route_info(route_number)
    
    if not route_info:
        if ctx:
            ctx.warning(f"Route {route_number} not found")
        logger.warning(f"Route not found: {route_number}")
        return json.dumps({"error": f"Route {route_number} not found"}, indent=2)
    
    stops = route_info.get('stops', [])
    
    if ctx:
        ctx.info(f"Route {route_number} has {len(stops)} stops")
        ctx.debug(f"Sending {len(stops)} stops to client")
    logger.info(f"Retrieved {len(stops)} stops for route {route_number}")
    
    response = {
        "route_number": route_number,
        "route_name": route_info.get('route_name', ''),
        "total_stops": len(stops),
        "stops": stops
    }
    
    return json.dumps(response, indent=2, ensure_ascii=False)

@mcp.tool()
def get_routes_for_stop(stop_name: str, ctx: Context = None) -> str:
    """
    Get all routes that pass through a specific stop
    
    Args:
        stop_name: Bus stop name
    
    Returns:
        JSON string with all routes serving this stop
    """
    if ctx:
        ctx.debug(f"Finding routes serving stop: {stop_name}")
    logger.debug(f"Finding routes for stop: {stop_name}")
    
    routes = get_routes_for_stop(stop_name)
    
    if ctx:
        ctx.info(f"Stop {stop_name} is served by {len(routes)} route(s)")
        ctx.debug(f"Sending {len(routes)} routes to client")
    logger.info(f"Found {len(routes)} routes for stop: {stop_name}")
    
    response = {
        "stop_name": stop_name,
        "total_routes": len(routes),
        "routes": routes
    }
    
    return json.dumps(response, indent=2, ensure_ascii=False)

# ================== SERVER STARTUP ==================

def main():
    """Main entry point for the MCP server"""
    logger.info("=" * 80)
    logger.info("Mo Bus MCP Server Starting")
    logger.info("=" * 80)
    logger.info(f"Total routes available: {len(ROUTES)}")
    logger.info(f"Total stops available: {len(STOPS)}")
    logger.info("Logging level: DEBUG - All operations will be tracked")
    logger.info("=" * 80)
    
    mcp.run()

if __name__ == "__main__":
    main()
