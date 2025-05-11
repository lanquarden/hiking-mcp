"""Wikiloc API integration for fetching hiking trails."""
from typing import Any, List, Tuple
import base64
import json
from pathlib import Path

import httpx
import simplekml
import wkbparse
from bs4 import BeautifulSoup

# Constants
WIKILOC_API_BASE = "https://es.wikiloc.com/wikiloc/find.do"
GOOGLE_MAPS_LOCATION = "https://www.google.com/maps/search/?api=1&query="
USER_AGENT = "wikiloc-app/1.0"
difficulty_translation = {
        "Fácil": "Easy",
        "Moderado": "Moderate",
        "Difícil": "Hard",
        "Muy Difícil": "Very Hard",
        "Solo expertos": "Experts Only"
}

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

def format_trail(trail: dict) -> str:
    """Format a trail feature into a readable string with the new keys."""
    difficulty = difficulty_translation.get(trail.get("Dificultad técnica", ""), "Unknown")
    return f"""
Title: {trail['title']}
URL: {trail['url']}
Distance: {trail['Distancia']} 
Elevation gain: {trail['Desnivel positivo']}
Elevation loss: {trail['Desnivel negativo']}
Difficulty : {difficulty}
Maximum altitude: {trail['Altitud máxima']}
TrailRank: {trail['TrailRank']}
Minimum altitude: {trail['Altitud mínima']}
Trail type: {trail['Tipo de ruta']}
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

def extract_geometry(html: str) -> dict:
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
                
                # Get trail name
                slug = Path(data["mapData"][0]["prettyURL"]).stem
                name = data["mapData"][0]["nom"]
                start_url = f"{GOOGLE_MAPS_LOCATION}{data['mapData'][0]['blat']},{data['mapData'][0]['blng']}"
                end_url = f"{GOOGLE_MAPS_LOCATION}{data['mapData'][0]['elat']},{data['mapData'][0]['elng']}"
                
                # Parse TWKB to GeoJSON
                geojson = wkbparse.twkb_to_geojson(twkb_geom)
                
                # Extract coordinates from GeoJSON LineString
                coords = []
                if geojson["type"] == "LineString":
                    coords = [(coord[0],coord[1], coord[2]) for coord in geojson["coordinates"]]
                    
                return {
                    "name": name,
                    "slug": slug,
                    "coordinates": coords,
                    "start_url": start_url,
                    "end_url": end_url
                }
            except (json.JSONDecodeError, KeyError, IndexError, base64.binascii.Error) as e:
                print(f"Error extracting geometry: {e}")
                continue
            
    return {}

def create_kml(name: str, slug: str, coordinates: List[Tuple[float, float, float]]):
    """Create a KML file from a list of coordinates."""
    
    kml = simplekml.Kml()
     # Create trail style
    trail_style = simplekml.Style()
    trail_style.linestyle.color = 'ff0000ff'  # Red color
    trail_style.linestyle.width = 3

    # Create placemark for the trail
    trail = kml.newlinestring(name=name, description='Hiking trail from WikiLoc')
    trail.coords = coordinates
    trail.style = trail_style
    
    # Create start and end markers if we have coordinates
    if coordinates:
        # Start marker
        start = kml.newpoint(name='Start', description='Starting point')
        start.coords = [(coordinates[0][0], coordinates[0][1], coordinates[0][2])]
        
        # End marker
        end = kml.newpoint(name='End', description='End point')
        end.coords = [(coordinates[-1][0], coordinates[-1][1], coordinates[-1][2])]
    
    # Save KML file
    kml_path = Path("routes") / f"{slug}.kml"
    kml.save(kml_path)
    return kml_path.absolute()

async def search_trails(query: str, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float, page: int = 1, max_results: int = 5) -> str:
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
        return "Unable to fetch trails or no trails found."

    if not data["spas"]:
        return "No trails found for this search."

    # Extract and sort the trails by TrailRank (descending order)
    trails = []
    for spa in data["spas"]:
        trail = {
            "title": spa["name"],
            "url": f"https://es.wikiloc.com{spa['prettyURL']}",
            "distance_km": spa.get("distance"),
            "slope": spa.get("slope"),
            "author": spa.get("author"),
            "location": spa.get("near"),
            "trailrank": spa.get("trailrank")
        }
        
        # Obtain the route details (HTML response)
        response = await make_wikiloc_request(trail["url"], {})
        if isinstance(response, str):  # Ensure we got HTML response
            details = extract_trail_statistics(response)
            # Add details to the 'trail' dictionary
            trail.update(details)
        
        trails.append(trail)

    # Format the top results
    top_trails = [format_trail(trail) for trail in trails[:max_results]]
    
    return "\n---\n".join(top_trails)
