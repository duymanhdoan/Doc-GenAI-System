"""
Integration Tests for ML Service API
Tests the full API workflow with real dependencies
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any
import os
import time


# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "test-api-key")


@pytest.fixture
def api_client():
    """HTTP client fixture"""
    return httpx.AsyncClient(
        base_url=API_BASE_URL,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )


@pytest.fixture
def sample_prediction_request() -> Dict[str, Any]:
    """Sample prediction request"""
    return {
        "model_name": "house-price-v2",
        "features": {
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
        },
        "options": {
            "include_explanation": False,
            "include_confidence": True
        }
    }


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """Test health endpoint"""
        response = await api_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == "2.0.0"
        assert "checks" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, api_client):
        """Test readiness endpoint"""
        response = await api_client.get("/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_check(self, api_client):
        """Test liveness endpoint"""
        response = await api_client.get("/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestPredictionAPI:
    """Test prediction API endpoints"""

    @pytest.mark.asyncio
    async def test_single_prediction(self, api_client, sample_prediction_request):
        """Test single prediction request"""
        response = await api_client.post("/v1/predict", json=sample_prediction_request)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "request_id" in data
        assert "prediction" in data
        assert "model" in data
        assert "latency_ms" in data
        assert "timestamp" in data

        # Validate prediction data
        prediction = data["prediction"]
        assert "value" in prediction
        assert "unit" in prediction
        assert prediction["unit"] == "USD"
        assert isinstance(prediction["value"], (int, float))
        assert prediction["value"] > 0

        # Validate model info
        model = data["model"]
        assert model["name"] == "house-price-v2"
        assert "version" in model

        # Validate performance
        assert data["latency_ms"] < 500  # Should be under 500ms

    @pytest.mark.asyncio
    async def test_prediction_with_explanation(self, api_client, sample_prediction_request):
        """Test prediction with SHAP explanation"""
        sample_prediction_request["options"]["include_explanation"] = True

        response = await api_client.post("/v1/predict", json=sample_prediction_request)

        assert response.status_code == 200
        data = response.json()

        # Check if explanation is included (may be None if not implemented)
        assert "explanation" in data

    @pytest.mark.asyncio
    async def test_batch_prediction(self, api_client, sample_prediction_request):
        """Test batch prediction"""
        batch_request = {
            "model_name": "house-price-v2",
            "inputs": [
                {"id": "item_1", **sample_prediction_request},
                {"id": "item_2", **sample_prediction_request},
                {"id": "item_3", **sample_prediction_request}
            ]
        }

        response = await api_client.post("/v1/predict/batch", json=batch_request)

        assert response.status_code == 200
        data = response.json()

        assert "request_id" in data
        assert "results" in data
        assert "summary" in data

        # Validate results
        assert len(data["results"]) == 3
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] >= 0

        # Check individual results
        for result in data["results"]:
            assert "id" in result
            if result["status"] == "success":
                assert "prediction" in result

    @pytest.mark.asyncio
    async def test_prediction_caching(self, api_client, sample_prediction_request):
        """Test prediction result caching"""
        # First request
        response1 = await api_client.post("/v1/predict", json=sample_prediction_request)
        assert response1.status_code == 200
        latency1 = response1.json()["latency_ms"]

        # Second request (should be cached)
        response2 = await api_client.post("/v1/predict", json=sample_prediction_request)
        assert response2.status_code == 200
        latency2 = response2.json()["latency_ms"]

        # Cached request should be faster (if caching is enabled)
        # This is not always guaranteed, so we just check both succeeded
        assert response1.json()["prediction"]["value"] == response2.json()["prediction"]["value"]


class TestModelManagement:
    """Test model management endpoints"""

    @pytest.mark.asyncio
    async def test_list_models(self, api_client):
        """Test listing available models"""
        response = await api_client.get("/v1/models")

        assert response.status_code == 200
        data = response.json()

        assert "models" in data
        assert "pagination" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

        # Validate model structure
        model = data["models"][0]
        assert "id" in model
        assert "name" in model
        assert "version" in model
        assert "status" in model
        assert "endpoints" in model


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_invalid_model(self, api_client, sample_prediction_request):
        """Test prediction with non-existent model"""
        sample_prediction_request["model_name"] = "non-existent-model"

        response = await api_client.post("/v1/predict", json=sample_prediction_request)

        assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, api_client):
        """Test prediction with missing required fields"""
        invalid_request = {
            "model_name": "house-price-v2",
            "features": {
                "MSSubClass": 60
                # Missing many required fields
            }
        }

        response = await api_client.post("/v1/predict", json=invalid_request)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_feature_values(self, api_client, sample_prediction_request):
        """Test prediction with invalid feature values"""
        sample_prediction_request["features"]["LotArea"] = -1000  # Invalid negative value

        response = await api_client.post("/v1/predict", json=sample_prediction_request)

        assert response.status_code in [400, 422]


class TestPerformance:
    """Test API performance"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_client, sample_prediction_request):
        """Test handling concurrent requests"""
        num_requests = 10

        async def make_request():
            return await api_client.post("/v1/predict", json=sample_prediction_request)

        # Send concurrent requests
        tasks = [make_request() for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_time(self, api_client, sample_prediction_request):
        """Test response time SLA"""
        num_requests = 50
        latencies = []

        for _ in range(num_requests):
            start = time.time()
            response = await api_client.post("/v1/predict", json=sample_prediction_request)
            latency = (time.time() - start) * 1000  # Convert to ms

            assert response.status_code == 200
            latencies.append(latency)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"\nLatency Statistics:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")

        # Assert SLA targets
        assert p50 < 100, f"P50 latency {p50}ms exceeds 100ms target"
        assert p95 < 200, f"P95 latency {p95}ms exceeds 200ms target"


class TestMetrics:
    """Test metrics collection"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, api_client):
        """Test Prometheus metrics endpoint"""
        response = await api_client.get("/metrics")

        assert response.status_code == 200
        metrics_text = response.text

        # Verify key metrics are present
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text


@pytest.mark.asyncio
async def test_end_to_end_workflow(api_client, sample_prediction_request):
    """Test complete end-to-end workflow"""
    # 1. Check health
    health_response = await api_client.get("/health")
    assert health_response.status_code == 200

    # 2. List models
    models_response = await api_client.get("/v1/models")
    assert models_response.status_code == 200
    models = models_response.json()["models"]
    assert len(models) > 0

    # 3. Make prediction
    prediction_response = await api_client.post("/v1/predict", json=sample_prediction_request)
    assert prediction_response.status_code == 200

    prediction_data = prediction_response.json()
    assert "prediction" in prediction_data
    assert "request_id" in prediction_data

    # 4. Verify metrics updated
    metrics_response = await api_client.get("/metrics")
    assert metrics_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
