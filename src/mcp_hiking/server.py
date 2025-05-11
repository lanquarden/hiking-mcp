"""Model Context Protocol (MCP) server implementation for hiking trails."""
import os
from textwrap import dedent
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP
from mcp_hiking.api import wikiloc

# Initialize FastMCP server
mcp = FastMCP("wikiloc")

@mcp.tool()
async def get_trails(query: str, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float, page: int = 1, max_results: int = 5) -> str:
    """Search for trails on Wikiloc based on geographical area.

    Args:
        query: Search query (e.g. "Vall de Núria - Ribes de Freser").
        sw_lat: Latitude of the southwest corner of the bounding box.
        sw_lon: Longitude of the southwest corner of the bounding box.
        ne_lat: Latitude of the northeast corner of the bounding box.
        ne_lon: Longitude of the northeast corner of the bounding box.
        page: The page of results to fetch.
        max_results: The maximum number of results to return.

    Returns:
        A formatted string containing the trails found, with details like name, distance,
        difficulty, elevation gain/loss, etc.
    """
    return await wikiloc.search_trails(query, sw_lat, sw_lon, ne_lat, ne_lon, page, max_results)

@mcp.tool()
async def get_trail_geometry(trail_url: str) -> str:
    """Extract trail geometry from a Wikiloc trail URL and save it as KML while providing links to trail start and end.
    
    Args:
        trail_url: The URL of the Wikiloc trail.
        
    Returns:
        A GeometryResponse containing:
        - Path to the generated KML file
        - Google Maps URL to the start
        - Google Maps URL to the end
    """
    # Ensure route URL is valid
    # if not route_url.startswith("https://es.wikiloc.com/"):
    #     raise ValueError("Invalid Wikiloc URL. Must be a URL from es.wikiloc.com")
    
    # Get the HTML content
    html = await wikiloc.make_wikiloc_request(trail_url, {})
    if not isinstance(html, str):
        raise ValueError("Failed to fetch trail data")
        
    # Extract geometry
    geometry = wikiloc.extract_geometry(html)
    if not geometry:
        raise ValueError("No trail geometry found")
        
    # Create routes directory in current working directory if it doesn't exist
    output_dir = "routes"
    os.makedirs(output_dir, exist_ok=True)

    # Extract start and end urls
    start_url = geometry.pop("start_url", None)
    end_url = geometry.pop("end_url", None)

    # Create KML file
    kml_path = wikiloc.create_kml(**geometry)
    
    # Return response with KML path and coordinates
    return dedent(f"""
        KML file: {kml_path}
        Start url: {start_url}
        End url: {end_url}
        """)

def main():
    """Main function to run the server."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
