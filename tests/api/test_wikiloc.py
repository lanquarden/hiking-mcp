"""Tests for the Wikiloc API integration."""
import pytest
import httpx
from bs4 import BeautifulSoup
from mcp_hiking.api import wikiloc

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
