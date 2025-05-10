"""Model Context Protocol (MCP) server implementation for hiking routes."""
from mcp.server.fastmcp import FastMCP
from mcp_hiking.api import wikiloc

# Initialize FastMCP server
mcp = FastMCP("wikiloc")

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

def main():
    """Main function to run the server."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
