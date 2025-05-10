"""Tests for the Wikiloc API integration."""
import os
import pytest
import httpx
from bs4 import BeautifulSoup
from mcp_hiking.api import wikiloc
from mcp_hiking.server import get_route_geometry, GeometryResponse

@pytest.mark.asyncio
async def test_make_wikiloc_request(mock_wikiloc_response, respx_mock):
    """Test making requests to the Wikiloc API."""
    url = "https://es.wikiloc.com/wikiloc/find.do"
    respx_mock.get(url).mock(return_value=httpx.Response(
        status_code=200,
        json=mock_wikiloc_response,
        headers={"Content-Type": "application/json"}
    ))
    
    result = await wikiloc.make_wikiloc_request(url, {})
    assert result == mock_wikiloc_response

def test_extract_trail_statistics(mock_trail_html):
    """Test extracting trail statistics from HTML."""
    stats = wikiloc.extract_trail_statistics(mock_trail_html)
    
    assert stats["Dificultad técnica"] == "Moderado"
    assert stats["Distancia"] == "10.5 km"
    assert stats["Desnivel positivo"] == "500 m"

def test_format_route():
    """Test formatting a route into a readable string."""
    route = {
        "title": "Test Trail",
        "url": "https://es.wikiloc.com/wikiloc/test-trail",
        "Distancia": "10.5 km",
        "Desnivel positivo": "500 m",
        "Desnivel negativo": "500 m",
        "Dificultad técnica": "Moderado",
        "Altitud máxima": "1500 m",
        "TrailRank": "85",
        "Altitud mínima": "1000 m",
        "Tipo de ruta": "Circular"
    }
    
    formatted = wikiloc.format_route(route)
    
    assert "Test Trail" in formatted
    assert "10.5 km" in formatted
    assert "Moderate" in formatted  # Check translation
    assert "TrailRank: 85" in formatted

@pytest.mark.asyncio
async def test_get_route_geometry(mock_route_html, respx_mock):
    """Test extracting route geometry and generating KML."""
    # Mock the API request
    url = "https://es.wikiloc.com/rutas-senderismo/test-route"
    respx_mock.get(url).mock(return_value=httpx.Response(
        status_code=200,
        text=mock_route_html,
        headers={"Content-Type": "text/html"}
    ))

    # Call the tool
    result = await get_route_geometry(url)

    # Verify the response is correct
    assert isinstance(result, GeometryResponse)
    assert result.kml_path.startswith("routes/")
    assert result.kml_path.endswith(".kml")
    assert isinstance(result.start_coordinates, tuple)
    assert isinstance(result.end_coordinates, tuple)
    assert len(result.start_coordinates) == 2
    assert len(result.end_coordinates) == 2

    # Verify the KML file was created
    assert os.path.exists(result.kml_path)
    with open(result.kml_path, 'r') as f:
        kml_content = f.read()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in kml_content
        assert '<kml' in kml_content
        assert '<coordinates>' in kml_content

    # Clean up the test file
    os.remove(result.kml_path)
    if not os.listdir('routes'):
        os.rmdir('routes')
