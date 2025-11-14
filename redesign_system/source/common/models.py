"""
Common Pydantic Models
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# Enums
# ============================================================================

class UserRole(str, Enum):
    """User roles"""
    USER = "user"
    ADMIN = "admin"
    ANALYST = "analyst"


class UserStatus(str, Enum):
    """User status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class SubscriptionTier(str, Enum):
    """Subscription tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ModelType(str, Enum):
    """Model types"""
    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    NLP = "nlp"


class ModelStatus(str, Enum):
    """Model status"""
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    """Fraud risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# User Models
# ============================================================================

class User(BaseModel):
    """User model"""
    user_id: str
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    organization_id: Optional[str] = None
    preferences: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class Organization(BaseModel):
    """Organization model"""
    organization_id: str
    name: str
    slug: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    subscription_status: str = "active"
    monthly_request_limit: int = 1000
    monthly_request_used: int = 0
    settings: Dict[str, Any] = {}

    class Config:
        from_attributes = True


# ============================================================================
# Request/Response Models
# ============================================================================

class PredictionRequest(BaseModel):
    """Generic prediction request"""
    model_name: str
    model_version: Optional[str] = None
    features: Dict[str, Any]
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    """Generic prediction response"""
    request_id: str
    prediction: Dict[str, Any]
    model: Dict[str, str]
    explanation: Optional[Dict[str, Any]] = None
    latency_ms: int
    timestamp: datetime


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""
    model_name: str
    model_version: Optional[str] = None
    inputs: List[Dict[str, Any]] = Field(..., max_items=1000)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response"""
    error: Dict[str, Any]
    request_id: str
    timestamp: datetime


# ============================================================================
# Document Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Document upload request"""
    document_type: Optional[str] = None
    language: str = "en"
    options: Dict[str, Any] = Field(
        default_factory=lambda: {
            "ocr_enabled": True,
            "extract_tables": True,
            "extract_entities": True,
            "generate_summary": True
        }
    )


class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_id: str
    user_id: str
    organization_id: Optional[str] = None
    filename: str
    original_filename: str
    file_size_bytes: int
    content_type: str
    s3_bucket: str
    s3_key: str
    document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    language: str = "en"
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    page_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentProcessingStage(BaseModel):
    """Document processing stage"""
    stage: str
    status: str
    duration_ms: Optional[int] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class DocumentStatus(BaseModel):
    """Document processing status"""
    document_id: str
    status: ProcessingStatus
    progress: Dict[str, Any]
    pipeline_stages: List[DocumentProcessingStage]
    total_duration_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExtractedEntity(BaseModel):
    """Extracted entity"""
    type: str
    value: str
    confidence: float
    normalized_value: Optional[Any] = None
    location: Optional[Dict[str, Any]] = None


class DocumentResult(BaseModel):
    """Document processing result"""
    document_id: str
    status: ProcessingStatus
    document_type: str
    metadata: Dict[str, Any]
    ocr_result: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    entities: List[ExtractedEntity] = []
    extracted_data: Dict[str, Any] = {}
    generated_summary: Optional[str] = None
    output_files: Dict[str, str] = {}
    quality_metrics: Dict[str, Any] = {}


# ============================================================================
# Fraud Models
# ============================================================================

class TransactionScoreRequest(BaseModel):
    """Fraud score request"""
    transaction_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    timestamp: datetime
    merchant: Dict[str, Any]
    customer: Dict[str, Any]
    payment_method: Dict[str, Any]
    options: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "include_explanation": True,
            "threshold": 0.7
        }
    )


class FraudScoreResponse(BaseModel):
    """Fraud score response"""
    transaction_id: str
    fraud_score: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel
    decision: str  # approve, decline, review
    confidence: float
    factors: Dict[str, List[str]]
    feature_importance: Optional[List[Dict[str, Any]]] = None
    recommendations: List[str]
    model_version: str
    processing_time_ms: int
    timestamp: datetime


class FraudFeedback(BaseModel):
    """Fraud feedback"""
    transaction_id: str
    actual_fraud: bool
    feedback_type: str
    notes: Optional[str] = None
    submitted_by: str


# ============================================================================
# ML Model Models
# ============================================================================

class MLModelMetadata(BaseModel):
    """ML Model metadata"""
    model_id: str
    name: str
    version: str
    type: ModelType
    algorithm: Optional[str] = None
    framework: Optional[str] = None
    status: ModelStatus = ModelStatus.DRAFT
    model_uri: str
    model_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    hyperparameters: Optional[Dict[str, Any]] = None
    validation_metrics: Optional[Dict[str, Any]] = None
    production_metrics: Optional[Dict[str, Any]] = None
    deployment_config: Optional[Dict[str, Any]] = None
    deployed_at: Optional[datetime] = None
    traffic_percentage: int = 0
    description: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
