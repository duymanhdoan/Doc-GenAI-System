"""
Application Settings
Configuration management using Pydantic BaseSettings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "ML Inference Service"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"  # development, staging, production
    DEBUG: bool = False

    # API
    API_PREFIX: str = "/v1"
    CORS_ORIGINS: List[str] = ["*"]

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: Optional[str] = None

    # S3
    MODEL_BUCKET: str = "doc-genai-models-prod"
    DOCUMENT_BUCKET: str = "doc-genai-documents-prod"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/docgenai"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # DynamoDB
    DYNAMODB_TABLE_PREFIX: str = "docgenai-prod"
    SESSIONS_TABLE: str = "sessions"
    FEATURE_FLAGS_TABLE: str = "feature-flags"
    DOCUMENT_METADATA_TABLE: str = "document-metadata"

    # Redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    REDIS_TTL: int = 300  # 5 minutes

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_DAY: int = 10000

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "ml-inference-service"
    OTEL_TRACES_EXPORTER: str = "otlp"
    OTEL_METRICS_EXPORTER: str = "otlp"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Model Settings
    MODEL_WARMUP: bool = True
    MODEL_CACHE_TTL: int = 3600  # 1 hour
    PREDICTION_CACHE_TTL: int = 300  # 5 minutes

    # Batch Settings
    MAX_BATCH_SIZE: int = 1000
    BATCH_TIMEOUT_SECONDS: int = 300

    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60

    # SageMaker (optional)
    SAGEMAKER_ENDPOINT: Optional[str] = None

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_REGION: str = "us-east-1"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
