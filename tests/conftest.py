"""Shared pytest fixtures for testing."""
import pytest
from httpx import AsyncClient

@pytest.fixture
def mock_wikiloc_response():
    """Sample Wikiloc API response for testing."""
    return {
        "spas": [
            {
                "name": "Test Trail",
                "prettyURL": "/wikiloc/test-trail",
                "distance": "10.5 km",
                "slope": "500m",
                "author": "TestUser",
                "near": "Test Location",
                "trailrank": "85"
            }
        ]
    }

@pytest.fixture
def mock_trail_html():
    """Sample trail HTML for testing."""
    return '''
    <section id="trail-data">
        <dl class="data-items">
            <div class="d-item">
                <dt>Dificultad técnica</dt>
                <dd>Moderado</dd>
            </div>
            <div class="d-item">
                <dt>Distancia</dt>
                <dd>10.5 km</dd>
            </div>
            <div class="d-item">
                <dt>Desnivel positivo</dt>
                <dd>500 m</dd>
            </div>
        </dl>
    </section>
    '''
