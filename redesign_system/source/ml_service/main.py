"""
ML Inference Service - FastAPI Application
Redesigned for production with AWS EKS deployment
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
import time
import asyncio
import hashlib
import json

# AWS SDK
import boto3
from botocore.exceptions import ClientError

# ML Libraries
import joblib
import numpy as np
from sklearn.base import BaseEstimator

# Observability
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
import structlog

# Caching
import redis.asyncio as redis

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Circuit breaker
from circuitbreaker import circuit

# Configuration
from config.settings import settings
from common.auth import verify_api_key, get_current_user
from common.models import User, PredictionRequest, PredictionResponse
from common.exceptions import ModelNotFoundError, PredictionError
from common.utils import calculate_features_hash

# Initialize structured logging
logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Inference Service",
    description="Production-ready ML inference API with monitoring and scaling",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

PREDICTION_COUNT = Counter(
    'model_prediction_total',
    'Total predictions',
    ['model', 'status']
)

PREDICTION_LATENCY = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration',
    ['model']
)

MODEL_LOAD_TIME = Gauge(
    'model_load_time_seconds',
    'Time to load model',
    ['model']
)

ACTIVE_REQUESTS = Gauge(
    'active_requests',
    'Number of active requests'
)

# OpenTelemetry
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Global state
class ApplicationState:
    """Application state management"""
    def __init__(self):
        self.models: Dict[str, BaseEstimator] = {}
        self.model_metadata: Dict[str, Dict] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.s3_client = None
        self.dynamodb = None
        self.ready = False

state = ApplicationState()


# ============================================================================
# Pydantic Models
# ============================================================================

class HouseFeatures(BaseModel):
    """House features for price prediction"""
    MSSubClass: int = Field(..., ge=20, le=190, description="Building class")
    MSZoning: str = Field(..., description="General zoning classification")
    LotArea: int = Field(..., ge=1300, le=215245, description="Lot size in square feet")
    LotShape: str = Field(..., description="General shape of property")
    LandContour: str = Field(..., description="Flatness of the property")
    Utilities: str = Field(..., description="Type of utilities available")
    LotConfig: str = Field(..., description="Lot configuration")
    LandSlope: str = Field(..., description="Slope of property")
    Neighborhood: str = Field(..., description="Physical locations")
    Condition1: str = Field(..., description="Proximity to various conditions")
    BldgType: str = Field(..., description="Type of dwelling")

    class Config:
        schema_extra = {
            "example": {
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
        }


class PredictRequest(BaseModel):
    """Prediction request"""
    model_name: str = Field(default="house-price-v2", description="Model name")
    model_version: Optional[str] = Field(default=None, description="Model version")
    features: HouseFeatures = Field(..., description="Input features")
    options: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"include_explanation": False, "include_confidence": True}
    )


class BatchPredictRequest(BaseModel):
    """Batch prediction request"""
    model_name: str = Field(default="house-price-v2")
    model_version: Optional[str] = Field(default=None)
    inputs: List[Dict[str, Any]] = Field(..., max_items=1000, description="Batch inputs")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    """Prediction response"""
    request_id: str
    prediction: Dict[str, Any]
    model: Dict[str, str]
    explanation: Optional[Dict[str, Any]] = None
    latency_ms: int
    timestamp: datetime

    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_7x9k2m4n5p",
                "prediction": {
                    "value": 208500.50,
                    "unit": "USD",
                    "confidence": 0.92
                },
                "model": {
                    "name": "house-price-v2",
                    "version": "1.2.0",
                    "deployed_at": "2025-11-01T10:30:00Z"
                },
                "latency_ms": 45,
                "timestamp": "2025-11-14T08:30:15Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    checks: Dict[str, str]
    uptime_seconds: int


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    version: str
    type: str
    status: str
    description: str
    created_at: datetime
    updated_at: datetime
    metrics: Dict[str, float]
    endpoints: Dict[str, str]


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting ML Inference Service", version="2.0.0")

    try:
        # Initialize AWS clients
        state.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
        state.dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)

        # Initialize Redis
        if settings.REDIS_URL:
            state.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connected")

        # Load models
        await load_models()

        state.ready = True
        logger.info("ML Inference Service started successfully")

    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down ML Inference Service")

    if state.redis_client:
        await state.redis_client.close()

    logger.info("ML Inference Service stopped")


# ============================================================================
# Model Management
# ============================================================================

@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
async def load_model_from_s3(model_name: str, version: str) -> BaseEstimator:
    """Load model from S3 with circuit breaker"""
    with tracer.start_as_current_span("load_model_from_s3") as span:
        span.set_attribute("model.name", model_name)
        span.set_attribute("model.version", version)

        start_time = time.time()

        try:
            # Download from S3
            bucket = settings.MODEL_BUCKET
            key = f"models/{model_name}/{version}/model.pkl"

            logger.info("Loading model from S3", bucket=bucket, key=key)

            response = state.s3_client.get_object(Bucket=bucket, Key=key)
            model_data = response['Body'].read()

            # Load model
            model = joblib.loads(model_data)

            load_time = time.time() - start_time
            MODEL_LOAD_TIME.labels(model=model_name).set(load_time)

            logger.info(
                "Model loaded successfully",
                model=model_name,
                version=version,
                load_time=load_time
            )

            return model

        except ClientError as e:
            logger.error("Failed to load model from S3", error=str(e))
            raise ModelNotFoundError(f"Model {model_name}:{version} not found")


async def load_models():
    """Load all active models"""
    logger.info("Loading models")

    # Load default model
    try:
        model = await load_model_from_s3("house-price-v2", "1.2.0")
        state.models["house-price-v2"] = model
        state.model_metadata["house-price-v2"] = {
            "version": "1.2.0",
            "deployed_at": datetime.utcnow().isoformat(),
            "type": "regression",
            "status": "active"
        }
        logger.info("Default model loaded", model="house-price-v2")

    except Exception as e:
        logger.error("Failed to load default model", error=str(e))

    # TODO: Load additional models from database
    # Query DynamoDB for active models and load them


def get_model(model_name: str) -> BaseEstimator:
    """Get model from cache"""
    if model_name not in state.models:
        raise ModelNotFoundError(f"Model {model_name} not found")
    return state.models[model_name]


# ============================================================================
# Caching
# ============================================================================

async def get_cached_prediction(cache_key: str) -> Optional[Dict]:
    """Get cached prediction"""
    if not state.redis_client:
        return None

    try:
        cached = await state.redis_client.get(cache_key)
        if cached:
            logger.debug("Cache hit", cache_key=cache_key)
            return json.loads(cached)
    except Exception as e:
        logger.warning("Cache get failed", error=str(e))

    return None


async def cache_prediction(cache_key: str, prediction: Dict, ttl: int = 300):
    """Cache prediction result"""
    if not state.redis_client:
        return

    try:
        await state.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(prediction)
        )
        logger.debug("Prediction cached", cache_key=cache_key)
    except Exception as e:
        logger.warning("Cache set failed", error=str(e))


def generate_cache_key(model_name: str, features: Dict) -> str:
    """Generate cache key for prediction"""
    features_str = json.dumps(features, sort_keys=True)
    features_hash = hashlib.sha256(features_str.encode()).hexdigest()
    return f"prediction:{model_name}:{features_hash}"


# ============================================================================
# Prediction Logic
# ============================================================================

async def make_prediction(
    model_name: str,
    features: Dict[str, Any],
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """Make prediction with caching"""
    with tracer.start_as_current_span("make_prediction") as span:
        span.set_attribute("model.name", model_name)

        start_time = time.time()

        # Check cache
        cache_key = generate_cache_key(model_name, features)
        cached_result = await get_cached_prediction(cache_key)
        if cached_result:
            return cached_result

        # Get model
        model = get_model(model_name)

        # Prepare features
        # TODO: Feature engineering and transformation
        feature_vector = prepare_features(features)

        # Make prediction
        try:
            prediction_value = model.predict([feature_vector])[0]

            # Calculate confidence (if available)
            confidence = None
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba([feature_vector])[0]
                confidence = float(np.max(proba))

            result = {
                "value": float(prediction_value),
                "unit": "USD",
                "confidence": confidence
            }

            # Cache result
            await cache_prediction(cache_key, result)

            latency_ms = int((time.time() - start_time) * 1000)

            # Metrics
            PREDICTION_COUNT.labels(model=model_name, status="success").inc()
            PREDICTION_LATENCY.labels(model=model_name).observe(time.time() - start_time)

            logger.info(
                "Prediction completed",
                model=model_name,
                latency_ms=latency_ms
            )

            return result

        except Exception as e:
            PREDICTION_COUNT.labels(model=model_name, status="error").inc()
            logger.error("Prediction failed", model=model_name, error=str(e))
            raise PredictionError(f"Prediction failed: {str(e)}")


def prepare_features(features: Dict[str, Any]) -> np.ndarray:
    """Prepare features for model input"""
    # TODO: Implement proper feature engineering
    # This is a placeholder - actual implementation depends on model
    return np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])


# ============================================================================
# API Endpoints
# ============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and metrics"""
    start_time = time.time()
    ACTIVE_REQUESTS.inc()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)

    ACTIVE_REQUESTS.dec()

    return response


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "ML Inference Service",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    checks = {
        "database": "healthy" if state.ready else "unhealthy",
        "cache": "healthy" if state.redis_client else "degraded",
        "model_loader": "healthy" if state.models else "unhealthy",
        "storage": "healthy" if state.s3_client else "unhealthy"
    }

    status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"

    return HealthResponse(
        status=status,
        version="2.0.0",
        timestamp=datetime.utcnow(),
        checks=checks,
        uptime_seconds=int(time.time())  # TODO: Track actual uptime
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if not state.ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@app.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/predict", response_model=PredictResponse)
@limiter.limit("100/minute")
async def predict(
    request: Request,
    body: PredictRequest,
    user: User = Depends(get_current_user)
):
    """Make single prediction"""
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    logger.info(
        "Prediction request received",
        request_id=request_id,
        user_id=user.user_id,
        model=body.model_name
    )

    start_time = time.time()

    try:
        # Make prediction
        prediction = await make_prediction(
            model_name=body.model_name,
            features=body.features.dict(),
            options=body.options
        )

        latency_ms = int((time.time() - start_time) * 1000)

        response = PredictResponse(
            request_id=request_id,
            prediction=prediction,
            model={
                "name": body.model_name,
                "version": state.model_metadata.get(body.model_name, {}).get("version", "unknown"),
                "deployed_at": state.model_metadata.get(body.model_name, {}).get("deployed_at", "")
            },
            explanation=None,  # TODO: SHAP explanations
            latency_ms=latency_ms,
            timestamp=datetime.utcnow()
        )

        return response

    except ModelNotFoundError as e:
        logger.warning("Model not found", model=body.model_name)
        raise HTTPException(status_code=404, detail=str(e))

    except PredictionError as e:
        logger.error("Prediction error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/predict/batch")
@limiter.limit("10/minute")
async def batch_predict(
    request: Request,
    body: BatchPredictRequest,
    user: User = Depends(get_current_user)
):
    """Batch prediction"""
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    logger.info(
        "Batch prediction request",
        request_id=request_id,
        user_id=user.user_id,
        batch_size=len(body.inputs)
    )

    start_time = time.time()

    results = []
    for idx, item in enumerate(body.inputs):
        try:
            prediction = await make_prediction(
                model_name=body.model_name,
                features=item.get("features", {}),
                options=body.options
            )
            results.append({
                "id": item.get("id", f"item_{idx}"),
                "prediction": prediction,
                "status": "success"
            })
        except Exception as e:
            results.append({
                "id": item.get("id", f"item_{idx}"),
                "error": str(e),
                "status": "failed"
            })

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "request_id": request_id,
        "results": results,
        "summary": {
            "total": len(results),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed")
        },
        "latency_ms": latency_ms,
        "timestamp": datetime.utcnow()
    }


@app.get("/v1/models", response_model=Dict[str, Any])
async def list_models(
    user: User = Depends(get_current_user),
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """List available models"""
    # TODO: Query from database
    models = []
    for name, metadata in state.model_metadata.items():
        models.append({
            "id": f"model_{name}",
            "name": name,
            "version": metadata.get("version"),
            "type": metadata.get("type"),
            "status": metadata.get("status"),
            "description": f"{name} prediction model",
            "created_at": metadata.get("deployed_at"),
            "updated_at": metadata.get("deployed_at"),
            "metrics": {},
            "endpoints": {
                "predict": "/v1/predict",
                "batch": "/v1/predict/batch"
            }
        })

    return {
        "models": models,
        "pagination": {
            "total": len(models),
            "page": page,
            "limit": limit,
            "total_pages": 1
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None
    )
