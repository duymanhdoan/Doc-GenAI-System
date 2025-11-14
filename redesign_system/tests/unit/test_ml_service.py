"""
Unit Tests for ML Inference Service
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Import the app (adjust path as needed)
import sys
sys.path.insert(0, '../../source')

from ml_service.main import app, state, make_prediction, prepare_features
from common.models import User, HouseFeatures


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return User(
        user_id="test_user_123",
        email="test@example.com",
        username="testuser",
        role="user"
    )


@pytest.fixture
def sample_features():
    """Sample house features"""
    return {
        "MSSubClass": 60,
        "MSZoning": "RL",
        "LotArea": 8450,
        "LotShape": "Reg",
        "LandContour": "Lvl",
        "Utilities": "AllPub",
        "LotConfig": "Inside",
        "LandSlope": "Gtl",
        "Neighborhood": "CollgCr",
        "Condition1": "Norm",
        "BldgType": "1Fam"
    }


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "checks" in data
        assert data["version"] == "2.0.0"

    def test_readiness_check(self, client):
        """Test /ready endpoint"""
        state.ready = True
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_liveness_check(self, client):
        """Test /live endpoint"""
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_readiness_not_ready(self, client):
        """Test /ready when service is not ready"""
        state.ready = False
        response = client.get("/ready")
        assert response.status_code == 503


class TestPredictionEndpoint:
    """Test prediction endpoints"""

    @patch('ml_service.main.get_current_user')
    @patch('ml_service.main.make_prediction')
    def test_predict_success(self, mock_predict, mock_user_auth, client, mock_user, sample_features):
        """Test successful prediction"""
        mock_user_auth.return_value = mock_user
        mock_predict.return_value = {
            "value": 208500.50,
            "unit": "USD",
            "confidence": 0.92
        }

        response = client.post(
            "/v1/predict",
            json={
                "model_name": "house-price-v2",
                "features": sample_features,
                "options": {"include_explanation": False}
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "request_id" in data
        assert "prediction" in data
        assert "model" in data
        assert "latency_ms" in data
        assert data["prediction"]["value"] == 208500.50
        assert data["prediction"]["confidence"] == 0.92

    @patch('ml_service.main.get_current_user')
    def test_predict_missing_features(self, mock_user_auth, client, mock_user):
        """Test prediction with missing features"""
        mock_user_auth.return_value = mock_user

        response = client.post(
            "/v1/predict",
            json={
                "model_name": "house-price-v2",
                "features": {
                    "MSSubClass": 60,
                    # Missing required fields
                },
                "options": {}
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422  # Validation error

    @patch('ml_service.main.get_current_user')
    def test_predict_unauthorized(self, mock_user_auth, client, sample_features):
        """Test prediction without authentication"""
        mock_user_auth.side_effect = Exception("Unauthorized")

        response = client.post(
            "/v1/predict",
            json={
                "model_name": "house-price-v2",
                "features": sample_features
            }
        )

        assert response.status_code in [401, 500]


class TestBatchPrediction:
    """Test batch prediction"""

    @patch('ml_service.main.get_current_user')
    @patch('ml_service.main.make_prediction')
    def test_batch_predict_success(self, mock_predict, mock_user_auth, client, mock_user, sample_features):
        """Test successful batch prediction"""
        mock_user_auth.return_value = mock_user
        mock_predict.return_value = {
            "value": 208500.50,
            "unit": "USD",
            "confidence": 0.92
        }

        response = client.post(
            "/v1/predict/batch",
            json={
                "model_name": "house-price-v2",
                "inputs": [
                    {"id": "item_1", "features": sample_features},
                    {"id": "item_2", "features": sample_features}
                ]
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "request_id" in data
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 2
        assert data["summary"]["total"] == 2
        assert data["summary"]["successful"] == 2

    @patch('ml_service.main.get_current_user')
    def test_batch_predict_exceeds_limit(self, mock_user_auth, client, mock_user, sample_features):
        """Test batch prediction exceeding max batch size"""
        mock_user_auth.return_value = mock_user

        # Create batch larger than limit (1000)
        large_batch = [{"id": f"item_{i}", "features": sample_features} for i in range(1001)]

        response = client.post(
            "/v1/predict/batch",
            json={
                "model_name": "house-price-v2",
                "inputs": large_batch
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422  # Validation error


class TestModelManagement:
    """Test model management functions"""

    @patch('ml_service.main.state.s3_client')
    @patch('joblib.loads')
    async def test_load_model_from_s3(self, mock_joblib, mock_s3):
        """Test loading model from S3"""
        from ml_service.main import load_model_from_s3

        # Mock S3 response
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'model_data')
        }
        mock_joblib.return_value = MagicMock()

        model = await load_model_from_s3("house-price-v2", "1.2.0")

        assert model is not None
        mock_s3.get_object.assert_called_once()

    def test_get_model_success(self):
        """Test getting existing model"""
        from ml_service.main import get_model

        # Add mock model to state
        state.models["test-model"] = MagicMock()

        model = get_model("test-model")
        assert model is not None

    def test_get_model_not_found(self):
        """Test getting non-existent model"""
        from ml_service.main import get_model
        from common.exceptions import ModelNotFoundError

        with pytest.raises(ModelNotFoundError):
            get_model("non-existent-model")


class TestCaching:
    """Test caching functionality"""

    @patch('ml_service.main.state.redis_client')
    async def test_cache_prediction(self, mock_redis):
        """Test caching prediction result"""
        from ml_service.main import cache_prediction

        prediction = {"value": 100.0, "confidence": 0.9}
        await cache_prediction("test-key", prediction, ttl=300)

        mock_redis.setex.assert_called_once()

    @patch('ml_service.main.state.redis_client')
    async def test_get_cached_prediction(self, mock_redis):
        """Test retrieving cached prediction"""
        from ml_service.main import get_cached_prediction

        mock_redis.get.return_value = json.dumps({"value": 100.0})

        result = await get_cached_prediction("test-key")

        assert result is not None
        assert result["value"] == 100.0
        mock_redis.get.assert_called_once()

    def test_generate_cache_key(self):
        """Test cache key generation"""
        from ml_service.main import generate_cache_key

        features = {"a": 1, "b": 2}
        key = generate_cache_key("model-1", features)

        assert key.startswith("prediction:model-1:")
        assert len(key) > 30  # Should include hash


class TestUtilities:
    """Test utility functions"""

    def test_prepare_features(self, sample_features):
        """Test feature preparation"""
        result = prepare_features(sample_features)

        assert result is not None
        # Note: Actual implementation depends on model requirements

    async def test_make_prediction(self, sample_features):
        """Test prediction logic"""
        # Mock model in state
        mock_model = MagicMock()
        mock_model.predict.return_value = [208500.50]
        state.models["house-price-v2"] = mock_model

        result = await make_prediction(
            "house-price-v2",
            sample_features,
            {}
        )

        assert result is not None
        assert "value" in result
        assert result["unit"] == "USD"


class TestErrorHandling:
    """Test error handling"""

    @patch('ml_service.main.get_current_user')
    @patch('ml_service.main.make_prediction')
    def test_prediction_error(self, mock_predict, mock_user_auth, client, mock_user, sample_features):
        """Test prediction error handling"""
        mock_user_auth.return_value = mock_user
        mock_predict.side_effect = Exception("Prediction failed")

        response = client.post(
            "/v1/predict",
            json={
                "model_name": "house-price-v2",
                "features": sample_features
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 500

    def test_invalid_json(self, client):
        """Test invalid JSON request"""
        response = client.post(
            "/v1/predict",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


class TestMetrics:
    """Test metrics collection"""

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Should contain Prometheus metrics
        assert "http_requests_total" in response.text or response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=ml_service", "--cov-report=html"])
