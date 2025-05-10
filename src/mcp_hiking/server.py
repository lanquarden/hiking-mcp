"""Model Context Protocol (MCP) server implementation for hiking routes."""
import os
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP
from mcp_hiking.api import wikiloc

# Initialize FastMCP server
mcp = FastMCP("wikiloc")

@dataclass
class GeometryResponse:
    """Response containing route geometry data."""
    kml_path: str
    start_coordinates: tuple[float, float]
    end_coordinates: tuple[float, float]

@mcp.tool()
async def get_routes(query: str, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float, page: int = 1, max_results: int = 5) -> str:
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
        A formatted string containing the routes found, with details like name, distance,
        difficulty, elevation gain/loss, etc.
    """
    return await wikiloc.search_routes(query, sw_lat, sw_lon, ne_lat, ne_lon, page, max_results)

@mcp.tool()
async def get_route_geometry(route_url: str) -> GeometryResponse:
    """Extract route geometry from a Wikiloc route URL and save it as KML.
    
    Args:
        route_url: The URL of the Wikiloc route.
        
    Returns:
        A GeometryResponse containing:
        - Path to the generated KML file
        - Start coordinates (lat, lon)
        - End coordinates (lat, lon)
    """
    # Ensure route URL is valid
    if not route_url.startswith("https://es.wikiloc.com/"):
        raise ValueError("Invalid Wikiloc URL. Must be a URL from es.wikiloc.com")
    
    # Get the HTML content
    html = await wikiloc.make_wikiloc_request(route_url, {})
    if not isinstance(html, str):
        raise ValueError("Failed to fetch route data")
        
    # Extract geometry
    coordinates = wikiloc.extract_geometry(html)
    if not coordinates:
        raise ValueError("No route geometry found")
        
    # Create routes directory in current working directory if it doesn't exist
    output_dir = "routes"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate KML filename from route URL
    route_id = route_url.split("/")[-1].split("-")[0]
    kml_path = os.path.join(output_dir, f"route_{route_id}.kml")
    # Convert to relative path
    kml_path = os.path.relpath(kml_path)
    
    # Create KML file
    wikiloc.create_kml(coordinates, kml_path)
    
    # Return response with KML path and coordinates
    return GeometryResponse(
        kml_path=kml_path,
        start_coordinates=(coordinates[0].lat, coordinates[0].lon),
        end_coordinates=(coordinates[-1].lat, coordinates[-1].lon)
    )

def main():
    """Main function to run the server."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
