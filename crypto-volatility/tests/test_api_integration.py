"""
Integration test for the FastAPI application.
Tests API endpoints without requiring a full model setup.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_predictor():
    """Mock predictor for testing."""
    import numpy as np

    mock = MagicMock()
    # Return numpy array with shape (1, 2) to match expected format
    mock.predict_proba.return_value = np.array([[0.7, 0.3]])  # 30% probability of spike
    mock.model_version = "test-model-v1"
    return mock


def test_health_endpoint_without_model(client):
    """Test health endpoint when model is not loaded."""
    # When predictor is None, health should return 503
    with patch("api.app.predictor", None):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["model_loaded"] is False


def test_health_endpoint_with_model(client, mock_predictor):
    """Test health endpoint when model is loaded."""
    with patch("api.app.predictor", mock_predictor):
        with patch("api.app.model_version", "test-model-v1"):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["model_loaded"] is True
            assert data["model_version"] == "test-model-v1"


def test_version_endpoint(client):
    """Test version endpoint."""
    with patch("api.app.model_version", "test-model-v1"):
        with patch("api.app.model_loaded_at", 1234567890.0):
            response = client.get("/version")
            assert response.status_code == 200
            data = response.json()
            assert "api_version" in data
            assert data["model_version"] == "test-model-v1"
            assert "python_version" in data


def test_predict_endpoint_without_model(client):
    """Test predict endpoint when model is not loaded."""
    with patch("api.app.predictor", None):
        response = client.post(
            "/predict",
            json={
                "price": 50000.0,
                "midprice": 50000.5,
                "return_1s": 0.0001,
                "return_5s": 0.0005,
                "return_30s": 0.002,
                "return_60s": 0.004,
                "volatility": 0.001,
                "trade_intensity": 2.5,
                "spread_abs": 1.0,
                "spread_rel": 0.00002,
                "order_book_imbalance": 0.1,
            },
        )
        assert response.status_code == 503


def test_predict_endpoint_with_model(client, mock_predictor):
    """Test predict endpoint with a loaded model."""
    with patch("api.app.predictor", mock_predictor):
        with patch("api.app.model_version", "test-model-v1"):
            response = client.post(
                "/predict",
                json={
                    "price": 50000.0,
                    "midprice": 50000.5,
                    "return_1s": 0.0001,
                    "return_5s": 0.0005,
                    "return_30s": 0.002,
                    "return_60s": 0.004,
                    "volatility": 0.001,
                    "trade_intensity": 2.5,
                    "spread_abs": 1.0,
                    "spread_rel": 0.00002,
                    "order_book_imbalance": 0.1,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "prediction" in data
            assert "probability" in data
            assert data["probability"] == 0.3  # From mock
            assert data["model_version"] == "test-model-v1"
            assert "timestamp" in data


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Prometheus metrics should be present
    assert "volatility_predictions_total" in response.text or len(response.text) > 0
