"""Wikiloc API integration for fetching hiking routes."""
from typing import Any, List, Tuple
import base64
import json
import os
import httpx
from bs4 import BeautifulSoup
import simplekml
import wkbparse

# Constants
WIKILOC_API_BASE = "https://es.wikiloc.com/wikiloc/find.do"
USER_AGENT = "wikiloc-app/1.0"
difficulty_translation = {
        "Fácil": "Easy",
        "Moderado": "Moderate",
        "Difícil": "Hard",
        "Muy Difícil": "Very Hard",
        "Solo expertos": "Experts Only"
}

class Coordinates:
    """Class to represent coordinates."""
    def __init__(self, lat: float, lon: float, alt: float = 0.0):
        self.lat = lat
        self.lon = lon
        self.alt = alt

    @classmethod
    def from_geojson(cls, coords: list) -> 'Coordinates':
        """Create a Coordinates instance from GeoJSON coordinates [lon, lat, alt]."""
        return cls(coords[1], coords[0], coords[2] if len(coords) > 2 else 0.0)

async def make_wikiloc_request(url: str, params: dict) -> str | dict[str, Any] | None:
    """Make a request to Wikiloc and return either HTML or JSON based on response."""
    headers = {
        "User-Agent": USER_AGENT
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return response.json()
            else:
                return response.text  # HTML or other format
        except Exception as e:
            print(f"Error in request: {e}")
            return None

def format_route(route: dict) -> str:
    """Format a route feature into a readable string with the new keys."""
    difficulty = difficulty_translation.get(route.get("Dificultad técnica", ""), "Unknown")
    return f"""
Title: {route['title']}
URL: {route['url']}
Distance: {route['Distancia']} 
Elevation gain: {route['Desnivel positivo']}
Elevation loss: {route['Desnivel negativo']}
Difficulty : {difficulty}
Maximum altitude: {route['Altitud máxima']}
TrailRank: {route['TrailRank']}
Minimum altitude: {route['Altitud mínima']}
Route type: {route['Tipo de ruta']}
"""

def extract_trail_statistics(html: str) -> dict:
    """Extracts trail statistics from Wikiloc HTML."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("section", id="trail-data")

    if not section:
        return {}

    data = {}
    for item in section.select("dl.data-items .d-item"):
        dt = item.find("dt")
        dd = item.find("dd")
        if not (dt and dd):
            continue

        key = dt.get_text(strip=True).replace('\xa0', ' ')

        # Special case: TrailRank
        if "TrailRank" in key:
            # Look for just the first <span> with number
            first_span = dd.find("span")
            value = first_span.get_text(strip=True) if first_span else ''
        else:
            # For other cases, extract all text from dd
            value = dd.get_text(strip=True).replace('\xa0', ' ')

        data[key] = value

    return data

def extract_geometry(html: str) -> List[Coordinates]:
    """Extract the geometry data from the Wikiloc HTML."""
    lines = html.split("\n")
    for line in lines:
        if "var mapData =" in line:
            try:
                # Find the JSON object
                start = line.find("=") + 1
                json_str = line[start:].strip().rstrip(";")
                data = json.loads(json_str)
                
                # Decode base64 geometry
                twkb_geom = base64.b64decode(data["mapData"][0]["geom"])
                
                # Parse TWKB to GeoJSON
                geojson = wkbparse.twkb_to_geojson(twkb_geom)
                
                # Extract coordinates from GeoJSON LineString
                if geojson["type"] == "LineString":
                    return [Coordinates.from_geojson(coord) for coord in geojson["coordinates"]]
                return []
            except (json.JSONDecodeError, KeyError, IndexError, base64.binascii.Error) as e:
                print(f"Error extracting geometry: {e}")
                continue
            
    return []

def create_kml(coordinates: List[Coordinates], output_file: str):
    """Create a KML file from a list of coordinates."""
    
    kml = simplekml.Kml()
    
    # Create route style
    route_style = simplekml.Style()
    route_style.linestyle.color = 'ff0000ff'  # Red color
    route_style.linestyle.width = 3
    
    # Create placemark for the route
    route = kml.newlinestring(name='Hiking Route', description='Route line')
    route.coords = [(c.lon, c.lat, c.alt) for c in coordinates]
    route.style = route_style
    
    # Create start and end markers if we have coordinates
    if coordinates:
        # Start marker
        start = kml.newpoint(name='Start', description='Starting point')
        start.coords = [(coordinates[0].lon, coordinates[0].lat, coordinates[0].alt)]
        
        # End marker
        end = kml.newpoint(name='End', description='End point')
        end.coords = [(coordinates[-1].lon, coordinates[-1].lat, coordinates[-1].alt)]
    
    # Save KML file
    kml.save(output_file)

async def search_routes(query: str, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float, page: int = 1, max_results: int = 5) -> str:
    """Search for routes on Wikiloc based on geographical area.

    Args:
        query: Search query (e.g. "Vall de Núria - Ribes de Freser").
        sw_lat: Latitude of the southwest corner of the bounding box.
        sw_lon: Longitude of the southwest corner of the bounding box.
        ne_lat: Latitude of the northeast corner of the bounding box.
        ne_lon: Longitude of the northeast corner of the bounding box.
        page: The page of results to fetch.
        max_results: The maximum number of results to return.

    Returns:
        A formatted string containing the routes found.
    """
    params = {
        "event": "map",
        "to": 25,
        "sw": f"{sw_lat},{sw_lon}",
        "ne": f"{ne_lat},{ne_lon}",
        "q": query,
        "page": page
    }

    # Make the request to the Wikiloc API
    url = WIKILOC_API_BASE
    data = await make_wikiloc_request(url, params)

    if not data or "spas" not in data:
        return "Unable to fetch routes or no routes found."

    if not data["spas"]:
        return "No routes found for this search."

    # Extract and sort the routes by TrailRank (descending order)
    routes = []
    for spa in data["spas"]:
        route = {
            "title": spa["name"],
            "url": f"https://es.wikiloc.com{spa['prettyURL']}",
            "distance_km": spa.get("distance"),
            "slope": spa.get("slope"),
            "author": spa.get("author"),
            "location": spa.get("near"),
            "trailrank": spa.get("trailrank")
        }
        
        # Obtain the route details (HTML response)
        response = await make_wikiloc_request(route["url"], {})
        if isinstance(response, str):  # Ensure we got HTML response
            details = extract_trail_statistics(response)
            # Add details to the 'route' dictionary
            route.update(details)
        
        routes.append(route)

    # Format the top results
    top_routes = [format_route(route) for route in routes[:max_results]]
    
    return "\n---\n".join(top_routes)
