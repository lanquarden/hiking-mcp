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
def mock_trail_statistics_html():
    """Sample trail statistics HTML section for testing extract_trail_statistics."""
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

@pytest.fixture
def mock_trail_html():
    """Load sample trail HTML with geometry data for testing."""
    with open('tests/resources/trail.html', 'r', encoding='utf-8') as f:
        return f.read()
