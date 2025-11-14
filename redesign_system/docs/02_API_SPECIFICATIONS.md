# API Specifications - Document Generation AI System

## Overview

This document defines the RESTful API specifications for all services in the redesigned system.

---

## 1. ML Inference Service API

### Base URL
```
Production: https://api.docgenai.com/v1
Staging: https://api-staging.docgenai.com/v1
```

### Authentication
```http
Authorization: Bearer <JWT_TOKEN>
X-API-Key: <API_KEY>
```

### 1.1 Predict (Synchronous)

**Endpoint**: `POST /predict`

**Description**: Make real-time prediction for a single input

**Request**:
```json
{
  "model_name": "house-price-v2",
  "model_version": "1.2.0",
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
    "include_explanation": true,
    "include_confidence": true
  }
}
```

**Response** (200 OK):
```json
{
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
  "explanation": {
    "method": "SHAP",
    "top_features": [
      {"name": "LotArea", "contribution": 15234.5},
      {"name": "Neighborhood", "contribution": 12500.0},
      {"name": "BldgType", "contribution": -3200.0}
    ]
  },
  "latency_ms": 45,
  "timestamp": "2025-11-14T08:30:15Z"
}
```

**Response** (400 Bad Request):
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Missing required feature: MSSubClass",
    "details": {
      "missing_features": ["MSSubClass"],
      "expected_schema": "house-price-v2-schema"
    }
  },
  "request_id": "req_7x9k2m4n5p",
  "timestamp": "2025-11-14T08:30:15Z"
}
```

**Response** (429 Too Many Requests):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit of 1000 requests per minute exceeded",
    "retry_after": 30
  },
  "request_id": "req_7x9k2m4n5p",
  "timestamp": "2025-11-14T08:30:15Z"
}
```

**Rate Limits**:
- Free tier: 100 requests/minute
- Pro tier: 1,000 requests/minute
- Enterprise: Custom

---

### 1.2 Batch Predict (Synchronous)

**Endpoint**: `POST /predict/batch`

**Description**: Make predictions for multiple inputs in a single request

**Request**:
```json
{
  "model_name": "house-price-v2",
  "model_version": "1.2.0",
  "inputs": [
    {
      "id": "item_1",
      "features": { /* ... */ }
    },
    {
      "id": "item_2",
      "features": { /* ... */ }
    }
  ],
  "options": {
    "include_explanation": false,
    "include_confidence": true
  }
}
```

**Response** (200 OK):
```json
{
  "request_id": "req_8a7b6c5d4e",
  "results": [
    {
      "id": "item_1",
      "prediction": {
        "value": 208500.50,
        "confidence": 0.92
      },
      "status": "success"
    },
    {
      "id": "item_2",
      "prediction": {
        "value": 181500.25,
        "confidence": 0.88
      },
      "status": "success"
    }
  ],
  "summary": {
    "total": 2,
    "successful": 2,
    "failed": 0
  },
  "latency_ms": 120,
  "timestamp": "2025-11-14T08:35:00Z"
}
```

**Limits**:
- Max batch size: 1000 items
- Max request size: 10 MB

---

### 1.3 Async Predict

**Endpoint**: `POST /predict/async`

**Description**: Submit prediction job for asynchronous processing

**Request**:
```json
{
  "model_name": "house-price-v2",
  "inputs": [ /* ... */ ],
  "callback_url": "https://your-app.com/webhooks/predictions",
  "options": {
    "priority": "normal",
    "timeout_seconds": 300
  }
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "job_9f8e7d6c5b",
  "status": "accepted",
  "estimated_completion": "2025-11-14T08:40:00Z",
  "status_url": "/jobs/job_9f8e7d6c5b",
  "timestamp": "2025-11-14T08:35:00Z"
}
```

**Webhook Callback** (when complete):
```json
{
  "job_id": "job_9f8e7d6c5b",
  "status": "completed",
  "results": [ /* predictions */ ],
  "completed_at": "2025-11-14T08:38:45Z"
}
```

---

### 1.4 List Models

**Endpoint**: `GET /models`

**Description**: List all available models

**Query Parameters**:
- `status` (optional): `active`, `deprecated`, `experimental`
- `type` (optional): `regression`, `classification`, `nlp`
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)

**Response** (200 OK):
```json
{
  "models": [
    {
      "id": "model_house_price_v2",
      "name": "house-price-v2",
      "version": "1.2.0",
      "type": "regression",
      "status": "active",
      "description": "House price prediction model using LightGBM",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-11-01T10:30:00Z",
      "metrics": {
        "rmse": 12345.67,
        "mae": 8901.23,
        "r2": 0.92
      },
      "endpoints": {
        "predict": "/predict",
        "batch": "/predict/batch",
        "metadata": "/models/model_house_price_v2"
      }
    },
    {
      "id": "model_fraud_detection_v3",
      "name": "fraud-detection-v3",
      "version": "3.1.0",
      "type": "classification",
      "status": "active",
      "description": "Credit card fraud detection using ensemble model",
      "created_at": "2025-09-15T00:00:00Z",
      "updated_at": "2025-11-10T14:20:00Z",
      "metrics": {
        "precision": 0.98,
        "recall": 0.95,
        "f1_score": 0.965,
        "auc_roc": 0.99
      }
    }
  ],
  "pagination": {
    "total": 15,
    "page": 1,
    "limit": 20,
    "total_pages": 1
  }
}
```

---

### 1.5 Get Model Metadata

**Endpoint**: `GET /models/{model_id}`

**Description**: Get detailed metadata for a specific model

**Response** (200 OK):
```json
{
  "id": "model_house_price_v2",
  "name": "house-price-v2",
  "version": "1.2.0",
  "type": "regression",
  "status": "active",
  "description": "House price prediction model using LightGBM",
  "algorithm": "LightGBM Gradient Boosting",
  "framework": "scikit-learn",
  "input_schema": {
    "type": "object",
    "required": ["MSSubClass", "MSZoning", "LotArea"],
    "properties": {
      "MSSubClass": {"type": "integer", "minimum": 20, "maximum": 190},
      "MSZoning": {"type": "string", "enum": ["RL", "RM", "C", "FV", "RH"]},
      "LotArea": {"type": "integer", "minimum": 1300, "maximum": 215245}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "value": {"type": "number"},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    }
  },
  "training": {
    "dataset_size": 1460,
    "training_date": "2025-10-25T00:00:00Z",
    "hyperparameters": {
      "n_estimators": 500,
      "learning_rate": 0.05,
      "max_depth": 7
    }
  },
  "performance": {
    "validation_metrics": {
      "rmse": 12345.67,
      "mae": 8901.23,
      "r2": 0.92
    },
    "production_metrics": {
      "avg_latency_ms": 45,
      "p95_latency_ms": 85,
      "p99_latency_ms": 150,
      "requests_per_second": 850,
      "error_rate": 0.0005
    }
  },
  "artifacts": {
    "model_file": "s3://models/house-price-v2/model.pkl",
    "size_mb": 15.3,
    "checksum": "sha256:a3b2c1d4e5f6..."
  },
  "deployment": {
    "deployed_at": "2025-11-01T10:30:00Z",
    "deployment_strategy": "canary",
    "traffic_percentage": 100,
    "replicas": 5,
    "resources": {
      "cpu": "500m",
      "memory": "1Gi"
    }
  },
  "created_at": "2025-10-01T00:00:00Z",
  "updated_at": "2025-11-01T10:30:00Z"
}
```

---

### 1.6 Health Check

**Endpoint**: `GET /health`

**Description**: Service health check

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-11-14T08:45:00Z",
  "checks": {
    "database": "healthy",
    "cache": "healthy",
    "model_loader": "healthy",
    "storage": "healthy"
  },
  "uptime_seconds": 345600
}
```

---

### 1.7 Metrics

**Endpoint**: `GET /metrics`

**Description**: Prometheus metrics endpoint

**Response** (200 OK):
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/predict",status="200"} 125340

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.05"} 95234
http_request_duration_seconds_bucket{le="0.1"} 118456
http_request_duration_seconds_bucket{le="0.2"} 123890

# HELP model_prediction_total Total number of predictions
# TYPE model_prediction_total counter
model_prediction_total{model="house-price-v2",status="success"} 123456

# HELP model_inference_duration_seconds Model inference duration
# TYPE model_inference_duration_seconds histogram
model_inference_duration_seconds_bucket{model="house-price-v2",le="0.05"} 98765
```

---

## 2. Document Processing API

### Base URL
```
Production: https://api.docgenai.com/v1/documents
```

### 2.1 Upload Document

**Endpoint**: `POST /upload`

**Description**: Upload document for processing

**Request** (multipart/form-data):
```
file: <binary>
document_type: invoice | receipt | contract | id_card
language: en | vi
options: {
  "ocr_enabled": true,
  "extract_tables": true,
  "extract_entities": true,
  "generate_summary": true
}
```

**Response** (202 Accepted):
```json
{
  "document_id": "doc_a1b2c3d4e5",
  "status": "processing",
  "s3_location": "s3://documents/raw/doc_a1b2c3d4e5.pdf",
  "estimated_completion": "2025-11-14T08:50:00Z",
  "webhook_url": "/webhooks/documents/doc_a1b2c3d4e5",
  "status_url": "/documents/doc_a1b2c3d4e5/status",
  "timestamp": "2025-11-14T08:45:00Z"
}
```

---

### 2.2 Get Document Status

**Endpoint**: `GET /documents/{document_id}/status`

**Description**: Get processing status of a document

**Response** (200 OK):
```json
{
  "document_id": "doc_a1b2c3d4e5",
  "status": "completed",
  "progress": {
    "current_step": "generation",
    "total_steps": 5,
    "percentage": 100
  },
  "pipeline_stages": [
    {
      "stage": "upload",
      "status": "completed",
      "duration_ms": 450,
      "completed_at": "2025-11-14T08:45:01Z"
    },
    {
      "stage": "ocr",
      "status": "completed",
      "duration_ms": 2340,
      "completed_at": "2025-11-14T08:45:04Z",
      "metadata": {
        "pages_processed": 3,
        "confidence": 0.98
      }
    },
    {
      "stage": "classification",
      "status": "completed",
      "duration_ms": 125,
      "completed_at": "2025-11-14T08:45:04Z",
      "result": {
        "document_type": "invoice",
        "confidence": 0.96
      }
    },
    {
      "stage": "extraction",
      "status": "completed",
      "duration_ms": 890,
      "completed_at": "2025-11-14T08:45:05Z",
      "entities_found": 15
    },
    {
      "stage": "generation",
      "status": "completed",
      "duration_ms": 1200,
      "completed_at": "2025-11-14T08:45:06Z"
    }
  ],
  "total_duration_ms": 5005,
  "created_at": "2025-11-14T08:45:00Z",
  "completed_at": "2025-11-14T08:45:06Z"
}
```

---

### 2.3 Get Document Results

**Endpoint**: `GET /documents/{document_id}`

**Description**: Get processed document results

**Response** (200 OK):
```json
{
  "document_id": "doc_a1b2c3d4e5",
  "status": "completed",
  "document_type": "invoice",
  "metadata": {
    "filename": "invoice_2025_001.pdf",
    "file_size_bytes": 245680,
    "pages": 3,
    "language": "en",
    "uploaded_by": "user_123",
    "uploaded_at": "2025-11-14T08:45:00Z"
  },
  "ocr_result": {
    "confidence": 0.98,
    "text": "Full extracted text...",
    "pages": [
      {
        "page_number": 1,
        "text": "Page 1 text...",
        "confidence": 0.99,
        "bounding_boxes": [ /* ... */ ]
      }
    ]
  },
  "classification": {
    "document_type": "invoice",
    "confidence": 0.96,
    "sub_categories": ["commercial_invoice"]
  },
  "entities": [
    {
      "type": "DATE",
      "value": "2025-11-14",
      "confidence": 0.99,
      "normalized_value": "2025-11-14",
      "location": {
        "page": 1,
        "bounding_box": {"x": 100, "y": 50, "width": 80, "height": 20}
      }
    },
    {
      "type": "AMOUNT",
      "value": "$1,250.00",
      "confidence": 0.98,
      "normalized_value": 1250.00,
      "currency": "USD"
    },
    {
      "type": "ORGANIZATION",
      "value": "Acme Corp",
      "confidence": 0.95
    }
  ],
  "extracted_data": {
    "invoice_number": "INV-2025-001",
    "invoice_date": "2025-11-14",
    "due_date": "2025-12-14",
    "vendor": {
      "name": "Acme Corp",
      "address": "123 Main St, Anytown, USA",
      "tax_id": "12-3456789"
    },
    "customer": {
      "name": "ABC Company",
      "address": "456 Oak Ave, Somewhere, USA"
    },
    "line_items": [
      {
        "description": "Professional Services",
        "quantity": 10,
        "unit_price": 100.00,
        "total": 1000.00
      },
      {
        "description": "Consulting Fee",
        "quantity": 1,
        "unit_price": 250.00,
        "total": 250.00
      }
    ],
    "subtotal": 1250.00,
    "tax": 0.00,
    "total": 1250.00
  },
  "generated_summary": "This is a commercial invoice from Acme Corp to ABC Company for professional services totaling $1,250.00, dated November 14, 2025, with payment due by December 14, 2025.",
  "output_files": {
    "structured_json": "s3://documents/processed/doc_a1b2c3d4e5.json",
    "annotated_pdf": "s3://documents/annotated/doc_a1b2c3d4e5.pdf"
  },
  "quality_metrics": {
    "ocr_confidence": 0.98,
    "classification_confidence": 0.96,
    "extraction_confidence": 0.97,
    "validation_passed": true
  }
}
```

---

### 2.4 Generate Document

**Endpoint**: `POST /generate`

**Description**: Generate document from template and data

**Request**:
```json
{
  "template_id": "invoice_template_v2",
  "output_format": "pdf",
  "data": {
    "invoice_number": "INV-2025-100",
    "invoice_date": "2025-11-14",
    "customer": {
      "name": "John Doe",
      "address": "123 Elm St"
    },
    "items": [
      {"description": "Item 1", "price": 100},
      {"description": "Item 2", "price": 200}
    ],
    "total": 300
  },
  "options": {
    "include_watermark": false,
    "generate_qr_code": true
  }
}
```

**Response** (200 OK):
```json
{
  "document_id": "gen_x9y8z7w6v5",
  "status": "completed",
  "output": {
    "format": "pdf",
    "url": "https://cdn.docgenai.com/generated/gen_x9y8z7w6v5.pdf",
    "s3_location": "s3://documents/generated/gen_x9y8z7w6v5.pdf",
    "expires_at": "2025-11-15T08:45:00Z"
  },
  "metadata": {
    "template_id": "invoice_template_v2",
    "pages": 1,
    "file_size_bytes": 45230
  },
  "generated_at": "2025-11-14T08:45:00Z"
}
```

---

## 3. Fraud Detection API

### Base URL
```
Production: https://api.docgenai.com/v1/fraud
```

### 3.1 Score Transaction

**Endpoint**: `POST /score`

**Description**: Get fraud score for a transaction

**Request**:
```json
{
  "transaction_id": "txn_123456",
  "amount": 1250.00,
  "currency": "USD",
  "timestamp": "2025-11-14T08:45:00Z",
  "merchant": {
    "id": "merchant_789",
    "category": "electronics",
    "country": "US"
  },
  "customer": {
    "id": "customer_456",
    "email": "john@example.com",
    "ip_address": "192.168.1.1",
    "device_id": "device_abc123"
  },
  "payment_method": {
    "type": "credit_card",
    "last_4": "1234",
    "issuer": "visa"
  },
  "options": {
    "include_explanation": true,
    "threshold": 0.7
  }
}
```

**Response** (200 OK):
```json
{
  "transaction_id": "txn_123456",
  "fraud_score": 0.12,
  "risk_level": "low",
  "decision": "approve",
  "confidence": 0.95,
  "factors": {
    "positive_indicators": [
      "Customer has good transaction history",
      "Merchant is reputable",
      "Amount is within normal range"
    ],
    "negative_indicators": [
      "New device detected"
    ]
  },
  "feature_importance": [
    {"feature": "transaction_amount", "importance": 0.25, "value": 1250.00},
    {"feature": "customer_history", "importance": 0.20, "value": "good"},
    {"feature": "merchant_reputation", "importance": 0.18, "value": "high"},
    {"feature": "device_fingerprint", "importance": 0.15, "value": "new"}
  ],
  "recommendations": [
    "Approve transaction",
    "Monitor customer for next 24 hours"
  ],
  "model_version": "fraud-detection-v3.1.0",
  "processing_time_ms": 38,
  "timestamp": "2025-11-14T08:45:00Z"
}
```

**Response** (High Risk):
```json
{
  "transaction_id": "txn_789012",
  "fraud_score": 0.89,
  "risk_level": "high",
  "decision": "decline",
  "confidence": 0.92,
  "factors": {
    "positive_indicators": [],
    "negative_indicators": [
      "Unusual transaction amount (10x average)",
      "Location mismatch detected",
      "Velocity check failed (5 transactions in 10 minutes)",
      "Device fingerprint not recognized"
    ]
  },
  "recommended_actions": [
    "Decline transaction",
    "Contact customer for verification",
    "Flag account for review"
  ],
  "timestamp": "2025-11-14T08:46:00Z"
}
```

---

### 3.2 Batch Score

**Endpoint**: `POST /score/batch`

**Description**: Score multiple transactions

**Request**:
```json
{
  "transactions": [
    { "transaction_id": "txn_1", /* ... */ },
    { "transaction_id": "txn_2", /* ... */ }
  ]
}
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "transaction_id": "txn_1",
      "fraud_score": 0.12,
      "risk_level": "low",
      "decision": "approve"
    },
    {
      "transaction_id": "txn_2",
      "fraud_score": 0.78,
      "risk_level": "high",
      "decision": "decline"
    }
  ],
  "summary": {
    "total": 2,
    "approved": 1,
    "declined": 1,
    "requires_review": 0
  },
  "processing_time_ms": 95
}
```

---

### 3.3 Submit Feedback

**Endpoint**: `POST /feedback`

**Description**: Submit actual fraud label for model retraining

**Request**:
```json
{
  "transaction_id": "txn_123456",
  "actual_fraud": false,
  "feedback_type": "confirmed_legitimate",
  "notes": "Customer confirmed transaction",
  "submitted_by": "fraud_analyst_5"
}
```

**Response** (201 Created):
```json
{
  "feedback_id": "fb_a1b2c3d4",
  "transaction_id": "txn_123456",
  "status": "accepted",
  "will_be_used_for_retraining": true,
  "timestamp": "2025-11-14T08:50:00Z"
}
```

---

## 4. Common Error Responses

### 4.1 Validation Error (400)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "amount",
        "issue": "Must be a positive number",
        "provided_value": -100
      }
    ]
  },
  "request_id": "req_xyz123",
  "timestamp": "2025-11-14T09:00:00Z"
}
```

### 4.2 Unauthorized (401)
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired authentication token"
  },
  "request_id": "req_xyz124",
  "timestamp": "2025-11-14T09:01:00Z"
}
```

### 4.3 Forbidden (403)
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions to access this resource",
    "required_permission": "documents:read"
  },
  "request_id": "req_xyz125",
  "timestamp": "2025-11-14T09:02:00Z"
}
```

### 4.4 Not Found (404)
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "resource_type": "document",
    "resource_id": "doc_nonexistent"
  },
  "request_id": "req_xyz126",
  "timestamp": "2025-11-14T09:03:00Z"
}
```

### 4.5 Rate Limit (429)
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "limit": 1000,
    "window": "1 minute",
    "retry_after": 30
  },
  "request_id": "req_xyz127",
  "timestamp": "2025-11-14T09:04:00Z"
}
```

### 4.6 Internal Server Error (500)
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "incident_id": "inc_987654"
  },
  "request_id": "req_xyz128",
  "timestamp": "2025-11-14T09:05:00Z"
}
```

### 4.7 Service Unavailable (503)
```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Service temporarily unavailable",
    "retry_after": 60
  },
  "request_id": "req_xyz129",
  "timestamp": "2025-11-14T09:06:00Z"
}
```

---

## 5. API Versioning

### Strategy
- URL-based versioning: `/v1/`, `/v2/`
- Backward compatibility maintained for at least 12 months
- Deprecation notices sent 6 months in advance

### Version Lifecycle
```
v1.0 (Current - Stable)
  - Fully supported
  - Bug fixes and security updates

v0.9 (Deprecated)
  - Sunset date: 2025-12-31
  - No new features
  - Critical bug fixes only

v2.0 (Beta)
  - Early access for partners
  - Breaking changes from v1
  - Subject to changes
```

---

## 6. SDK Support

### Official SDKs
- Python: `pip install docgenai-sdk`
- JavaScript/TypeScript: `npm install @docgenai/sdk`
- Go: `go get github.com/docgenai/go-sdk`
- Java: Maven/Gradle dependency

### Example (Python)
```python
from docgenai import DocGenAI

client = DocGenAI(api_key="your_api_key")

# Make prediction
result = client.predict(
    model="house-price-v2",
    features={
        "MSSubClass": 60,
        "LotArea": 8450,
        # ...
    }
)

print(f"Prediction: ${result.value:.2f}")
print(f"Confidence: {result.confidence:.2%}")
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
