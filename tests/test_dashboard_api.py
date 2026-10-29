import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sunday.dashboard.api.main import app

client = TestClient(app)

def test_get_memory_stats_success():
    response = client.get("/api/memory/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_episodes": 0,
        "avg_surprise": 0.0,
        "high_surprise_count": 0
    }

@patch("sunday.dashboard.api.main._get_memory_data", side_effect=Exception("Database error"))
def test_get_memory_stats_error(mock_get_data):
    response = client.get("/api/memory/stats")
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error"}
