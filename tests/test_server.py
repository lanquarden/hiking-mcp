"""Tests for the MCP server functionality."""
import os
import pytest
import httpx
from mcp_hiking.server import get_trail_geometry

@pytest.mark.asyncio
async def test_get_trail_geometry(mock_trail_html, respx_mock):
    """Test extracting trail geometry and generating KML."""
    # Mock the API request
    url = "https://es.wikiloc.com/rutas-senderismo/test-trail"
    respx_mock.get(url).mock(return_value=httpx.Response(
        status_code=200,
        text=mock_trail_html,
        headers={"Content-Type": "text/html"}
    ))

    # Call the tool
    result = await get_trail_geometry(url)

    # Verify the response is correct
    assert isinstance(result, str)
    assert "KML file: routes/" in result
    assert ".kml" in result
    assert "Start url:" in result
    assert "End url:" in result

    # Extract the KML file path from the result
    import re
    kml_path = re.search(r'KML file: (.+\.kml)', result).group(1)
    
    # Verify the KML file was created
    assert os.path.exists(kml_path)
    with open(kml_path, 'r') as f:
        kml_content = f.read()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in kml_content
        assert '<kml' in kml_content
        assert '<coordinates>' in kml_content

    # Clean up the test file
    os.remove(kml_path)
    if not os.listdir('routes'):
        os.rmdir('routes')