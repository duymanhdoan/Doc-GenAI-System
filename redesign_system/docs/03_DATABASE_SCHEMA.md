# Database Schema Design

## Overview

This document defines the database schema for the redesigned Document Generation AI System, using a polyglot persistence approach with PostgreSQL (Aurora), DynamoDB, and Redis.

---

## 1. PostgreSQL (Amazon RDS Aurora) - Transactional Data

### 1.1 Users Table

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- user, admin, analyst
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, suspended, deleted
    email_verified BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20),
    organization_id UUID REFERENCES organizations(organization_id),

    -- Preferences
    preferences JSONB DEFAULT '{}',

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_organization ON users(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at);
```

### 1.2 Organizations Table

```sql
CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,

    -- Subscription
    subscription_tier VARCHAR(50) DEFAULT 'free', -- free, pro, enterprise
    subscription_status VARCHAR(20) DEFAULT 'active',
    subscription_start_date DATE,
    subscription_end_date DATE,

    -- Limits
    monthly_request_limit INTEGER DEFAULT 1000,
    monthly_request_used INTEGER DEFAULT 0,

    -- Contact
    billing_email VARCHAR(255),
    support_email VARCHAR(255),

    -- Settings
    settings JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_organizations_slug ON organizations(slug) WHERE deleted_at IS NULL;
```

### 1.3 API Keys Table

```sql
CREATE TABLE api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL, -- First chars for identification
    name VARCHAR(100) NOT NULL,

    -- Permissions
    scopes TEXT[] DEFAULT ARRAY['read'], -- read, write, admin

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 100,
    rate_limit_per_day INTEGER DEFAULT 10000,

    -- Usage
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count BIGINT DEFAULT 0,

    -- Lifecycle
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_last_used ON api_keys(last_used_at);
```

### 1.4 ML Models Table

```sql
CREATE TABLE ml_models (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Model info
    type VARCHAR(50) NOT NULL, -- regression, classification, nlp
    algorithm VARCHAR(100),
    framework VARCHAR(50), -- pytorch, tensorflow, scikit-learn

    -- Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, testing, active, deprecated

    -- Artifacts
    model_uri TEXT NOT NULL, -- S3 path
    model_size_bytes BIGINT,
    checksum VARCHAR(255),

    -- Schema
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,

    -- Training
    training_dataset_id UUID,
    training_date TIMESTAMP WITH TIME ZONE,
    hyperparameters JSONB,

    -- Performance metrics
    validation_metrics JSONB,
    production_metrics JSONB,

    -- Deployment
    deployment_config JSONB,
    deployed_at TIMESTAMP WITH TIME ZONE,
    traffic_percentage INTEGER DEFAULT 0,

    -- Metadata
    description TEXT,
    tags TEXT[],
    created_by UUID REFERENCES users(user_id),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(name, version)
);

CREATE INDEX idx_models_name_version ON ml_models(name, version);
CREATE INDEX idx_models_status ON ml_models(status);
CREATE INDEX idx_models_type ON ml_models(type);
```

### 1.5 Predictions Table

```sql
CREATE TABLE predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(100) UNIQUE NOT NULL,

    -- Request info
    user_id UUID REFERENCES users(user_id),
    organization_id UUID REFERENCES organizations(organization_id),
    model_id UUID NOT NULL REFERENCES ml_models(model_id),

    -- Input/Output
    input_features JSONB NOT NULL,
    prediction_value JSONB NOT NULL,
    confidence NUMERIC(5,4),

    -- Performance
    latency_ms INTEGER,

    -- Status
    status VARCHAR(20) DEFAULT 'completed', -- pending, completed, failed
    error_message TEXT,

    -- Metadata
    metadata JSONB,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Partitioning by month
    PARTITION BY RANGE (created_at)
);

-- Partitions (example for 2025)
CREATE TABLE predictions_2025_11 PARTITION OF predictions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE predictions_2025_12 PARTITION OF predictions
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE INDEX idx_predictions_user ON predictions(user_id, created_at DESC);
CREATE INDEX idx_predictions_model ON predictions(model_id, created_at DESC);
CREATE INDEX idx_predictions_request ON predictions(request_id);
```

### 1.6 Documents Table

```sql
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    user_id UUID NOT NULL REFERENCES users(user_id),
    organization_id UUID REFERENCES organizations(organization_id),

    -- Document info
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    file_size_bytes BIGINT,
    content_type VARCHAR(100),

    -- Storage
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key TEXT NOT NULL,
    s3_version_id VARCHAR(255),

    -- Classification
    document_type VARCHAR(100), -- invoice, receipt, contract, etc.
    classification_confidence NUMERIC(5,4),
    language VARCHAR(10),

    -- Processing
    processing_status VARCHAR(20) DEFAULT 'pending',
    -- pending, processing, completed, failed

    pipeline_version VARCHAR(50),

    -- Results
    ocr_text TEXT,
    ocr_confidence NUMERIC(5,4),
    extracted_entities JSONB,
    extracted_data JSONB,
    summary TEXT,

    -- Pages
    page_count INTEGER,

    -- Quality
    quality_score NUMERIC(5,4),
    validation_passed BOOLEAN,
    validation_errors JSONB,

    -- Metadata
    metadata JSONB,
    tags TEXT[],

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Partitioning by month
    PARTITION BY RANGE (created_at)
);

-- Partitions
CREATE TABLE documents_2025_11 PARTITION OF documents
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE INDEX idx_documents_user ON documents(user_id, created_at DESC);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_s3 ON documents(s3_bucket, s3_key);
```

### 1.7 Document Processing Jobs Table

```sql
CREATE TABLE document_processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id),

    -- Job info
    job_type VARCHAR(50) NOT NULL, -- ocr, classify, extract, generate
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5, -- 1 (highest) to 10 (lowest)

    -- Processing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,

    -- Worker
    worker_id VARCHAR(100),

    -- Results
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_document ON document_processing_jobs(document_id);
CREATE INDEX idx_jobs_status ON document_processing_jobs(status, priority, created_at);
```

### 1.8 Fraud Scores Table

```sql
CREATE TABLE fraud_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(255) NOT NULL,

    -- Request
    user_id UUID REFERENCES users(user_id),
    organization_id UUID REFERENCES organizations(organization_id),

    -- Transaction details
    amount NUMERIC(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    merchant_id VARCHAR(255),
    merchant_category VARCHAR(100),
    customer_id VARCHAR(255),
    payment_method VARCHAR(50),

    -- Scoring
    fraud_score NUMERIC(5,4) NOT NULL,
    risk_level VARCHAR(20) NOT NULL, -- low, medium, high, critical
    decision VARCHAR(20) NOT NULL, -- approve, decline, review
    model_version VARCHAR(50),
    confidence NUMERIC(5,4),

    -- Features
    features JSONB,
    feature_importance JSONB,

    -- Feedback
    actual_fraud BOOLEAN,
    feedback_submitted_at TIMESTAMP WITH TIME ZONE,
    feedback_submitted_by UUID REFERENCES users(user_id),

    -- Performance
    latency_ms INTEGER,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Partitioning
    PARTITION BY RANGE (created_at)
);

CREATE TABLE fraud_scores_2025_11 PARTITION OF fraud_scores
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE INDEX idx_fraud_transaction ON fraud_scores(transaction_id);
CREATE INDEX idx_fraud_org_date ON fraud_scores(organization_id, created_at DESC);
CREATE INDEX idx_fraud_risk ON fraud_scores(risk_level, created_at DESC);
```

### 1.9 Audit Logs Table

```sql
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Actor
    user_id UUID REFERENCES users(user_id),
    organization_id UUID REFERENCES organizations(organization_id),
    ip_address INET,
    user_agent TEXT,

    -- Action
    action VARCHAR(100) NOT NULL, -- create, read, update, delete
    resource_type VARCHAR(100) NOT NULL, -- user, document, model
    resource_id UUID,

    -- Details
    changes JSONB,
    metadata JSONB,

    -- Context
    request_id VARCHAR(100),
    session_id VARCHAR(100),

    -- Result
    status VARCHAR(20), -- success, failure
    error_message TEXT,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Partitioning by month for performance
    PARTITION BY RANGE (created_at)
);

CREATE TABLE audit_logs_2025_11 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
```

---

## 2. DynamoDB Tables

### 2.1 Sessions Table

```yaml
Table Name: sessions
Partition Key: session_id (String)
Billing Mode: On-Demand
TTL Attribute: expires_at

Attributes:
  session_id: String (PK)
  user_id: String
  organization_id: String
  data: Map
    - user_email: String
    - role: String
    - permissions: List
  ip_address: String
  user_agent: String
  created_at: Number (Unix timestamp)
  last_accessed_at: Number (Unix timestamp)
  expires_at: Number (Unix timestamp, TTL)

Global Secondary Indexes:
  - user_id-index:
      Partition Key: user_id
      Sort Key: created_at
      Projection: ALL
```

### 2.2 Feature Flags Table

```yaml
Table Name: feature_flags
Partition Key: flag_name (String)
Sort Key: environment (String)
Billing Mode: Provisioned (10 RCU, 5 WCU with auto-scaling)

Attributes:
  flag_name: String (PK)
  environment: String (SK) # dev, staging, prod
  enabled: Boolean
  description: String
  value: Map # Complex flag values
  rules: List # Targeting rules
    - condition: String
    - value: Boolean
  created_at: Number
  updated_at: Number
  created_by: String
```

### 2.3 Document Metadata Table

```yaml
Table Name: document_metadata
Partition Key: document_id (String)
Sort Key: version (Number)
Billing Mode: On-Demand

Attributes:
  document_id: String (PK)
  version: Number (SK)
  user_id: String
  organization_id: String
  filename: String
  content_type: String
  file_size: Number
  s3_location: String
  status: String
  processing_stages: List
    - stage: String
    - status: String
    - started_at: Number
    - completed_at: Number
    - duration_ms: Number
  tags: StringSet
  created_at: Number
  updated_at: Number
  deleted_at: Number

Global Secondary Indexes:
  - user_id-created_at-index:
      Partition Key: user_id
      Sort Key: created_at
      Projection: ALL

  - status-created_at-index:
      Partition Key: status
      Sort Key: created_at
      Projection: ALL

Streams: Enabled (NEW_AND_OLD_IMAGES)
```

### 2.4 API Usage Metrics Table

```yaml
Table Name: api_usage_metrics
Partition Key: api_key_id (String)
Sort Key: timestamp_hour (String) # Format: 2025-11-14T08
Billing Mode: On-Demand

Attributes:
  api_key_id: String (PK)
  timestamp_hour: String (SK)
  user_id: String
  organization_id: String

  # Aggregated metrics
  request_count: Number
  error_count: Number
  total_latency_ms: Number

  # By endpoint
  endpoint_metrics: Map
    - /predict:
        count: Number
        errors: Number
        avg_latency: Number
    - /documents:
        count: Number
        errors: Number
        avg_latency: Number

  created_at: Number
  ttl: Number # 90 days retention

Global Secondary Indexes:
  - organization_id-timestamp_hour-index:
      Partition Key: organization_id
      Sort Key: timestamp_hour
      Projection: ALL
```

### 2.5 Model Versions Table

```yaml
Table Name: model_versions
Partition Key: model_name (String)
Sort Key: version (String)
Billing Mode: On-Demand

Attributes:
  model_name: String (PK)
  version: String (SK)
  model_id: String
  status: String # draft, testing, active, deprecated
  s3_uri: String
  checksum: String
  size_bytes: Number

  # Metrics
  validation_metrics: Map
    - rmse: Number
    - mae: Number
    - r2: Number

  production_metrics: Map
    - avg_latency_ms: Number
    - p95_latency_ms: Number
    - error_rate: Number
    - total_requests: Number

  # Deployment
  traffic_percentage: Number
  deployed_at: Number

  created_at: Number
  updated_at: Number
  deprecated_at: Number

Global Secondary Indexes:
  - status-updated_at-index:
      Partition Key: status
      Sort Key: updated_at
      Projection: ALL
```

---

## 3. Redis (Amazon ElastiCache) - Caching

### 3.1 Cache Keys Structure

```
# User sessions
session:{session_id} -> JSON (TTL: 1 hour)

# API rate limiting
ratelimit:user:{user_id}:{minute} -> counter (TTL: 1 minute)
ratelimit:apikey:{api_key_id}:{minute} -> counter (TTL: 1 minute)

# Model predictions (cache frequent requests)
prediction:{model_name}:{hash(features)} -> JSON (TTL: 5 minutes)

# Document processing status
document:status:{document_id} -> JSON (TTL: 1 hour)

# Feature flags (hot cache)
feature_flag:{flag_name}:{environment} -> JSON (TTL: 1 minute)

# User profiles (hot data)
user:profile:{user_id} -> JSON (TTL: 10 minutes)

# API keys (authentication cache)
apikey:hash:{key_hash} -> JSON (TTL: 5 minutes)

# Distributed locks
lock:document:{document_id} -> 1 (TTL: 30 seconds)
lock:model:{model_name} -> 1 (TTL: 60 seconds)

# Leaderboards
leaderboard:predictions:daily:{date} -> Sorted Set
leaderboard:documents:monthly:{month} -> Sorted Set
```

### 3.2 Cache Patterns

```python
# Example: Prediction result caching
import hashlib
import json

def get_prediction_cache_key(model_name, features):
    features_str = json.dumps(features, sort_keys=True)
    features_hash = hashlib.sha256(features_str.encode()).hexdigest()
    return f"prediction:{model_name}:{features_hash}"

# Cache-aside pattern
def get_prediction(model_name, features):
    cache_key = get_prediction_cache_key(model_name, features)

    # Try cache first
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss - compute prediction
    prediction = model.predict(features)

    # Store in cache
    redis.setex(cache_key, 300, json.dumps(prediction))  # 5 min TTL

    return prediction
```

---

## 4. Schema Migration Strategy

### 4.1 Database Migrations (PostgreSQL)

```sql
-- Use Alembic for PostgreSQL migrations
-- Example migration: Add new column

-- Version: 2025_11_14_001_add_user_preferences
-- Up migration
ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';

-- Down migration
ALTER TABLE users DROP COLUMN preferences;
```

### 4.2 DynamoDB Schema Evolution

```yaml
# DynamoDB is schemaless, but maintain versioning
Strategy:
  - Add schema_version attribute to items
  - Implement backward-compatible reads
  - Migrate data lazily (on read/write)

Example:
  document_id: "doc_123"
  schema_version: 2  # Current version
  # ... other attributes

Migration Logic:
  - Read: Check schema_version, upgrade if needed
  - Write: Always write latest schema_version
  - Background job: Bulk migrate old versions
```

---

## 5. Data Retention Policies

### 5.1 Hot Data (< 30 days)

```
PostgreSQL:
  - predictions: Full data
  - documents: Full data with S3 objects
  - audit_logs: Full logs

DynamoDB:
  - sessions: Active sessions
  - document_metadata: Recent uploads
  - api_usage_metrics: Real-time metrics

Redis:
  - All cache entries (short TTL)
```

### 5.2 Warm Data (30-90 days)

```
PostgreSQL:
  - predictions: Move to separate partition
  - documents: S3 Intelligent-Tiering
  - audit_logs: Compressed storage

DynamoDB:
  - Archived to S3 via DynamoDB exports
```

### 5.3 Cold Data (> 90 days)

```
PostgreSQL:
  - predictions: Archive to S3 Parquet
  - documents: S3 Glacier
  - audit_logs: S3 Glacier Deep Archive

DynamoDB:
  - TTL-based deletion or S3 export
```

---

## 6. Backup Strategy

### 6.1 PostgreSQL (Aurora)

```yaml
Continuous Backup:
  - Point-in-time recovery: 35 days
  - Backup window: 03:00-04:00 UTC
  - Retention: 35 days

Snapshots:
  - Automated daily snapshots
  - Manual snapshots before major changes
  - Cross-region snapshot copy to us-west-2
  - Retention: 90 days

Backup Verification:
  - Monthly restore test to staging
  - Automated restore time measurement
```

### 6.2 DynamoDB

```yaml
Point-in-Time Recovery:
  - Enabled for all production tables
  - Retention: 35 days
  - Continuous backups

On-Demand Backups:
  - Daily backups via AWS Backup
  - Retention: 90 days
  - Tagged for compliance

Exports:
  - Monthly export to S3 (Parquet format)
  - Retention: 365 days
  - Used for analytics
```

### 6.3 Redis

```yaml
Persistence:
  - RDB snapshots: Every 6 hours
  - AOF: Disabled (cache-only data)
  - Retention: 7 days

Failover:
  - Multi-AZ automatic failover
  - Data loss: < 5 minutes (acceptable for cache)
```

---

## 7. Performance Optimization

### 7.1 PostgreSQL Indexes

```sql
-- Covering indexes for common queries
CREATE INDEX idx_predictions_user_model_date ON predictions(user_id, model_id, created_at DESC)
  INCLUDE (prediction_value, confidence);

-- Partial indexes for active records
CREATE INDEX idx_users_active ON users(email) WHERE deleted_at IS NULL;

-- BRIN indexes for time-series data
CREATE INDEX idx_audit_logs_created_at_brin ON audit_logs USING BRIN(created_at);

-- GIN indexes for JSONB queries
CREATE INDEX idx_documents_extracted_data ON documents USING GIN(extracted_data);
```

### 7.2 Query Optimization

```sql
-- Use EXPLAIN ANALYZE for query planning
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM predictions
WHERE user_id = 'uuid'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 100;

-- Materialized views for complex aggregations
CREATE MATERIALIZED VIEW mv_daily_prediction_stats AS
SELECT
  DATE_TRUNC('day', created_at) as date,
  model_id,
  COUNT(*) as prediction_count,
  AVG(latency_ms) as avg_latency,
  AVG(confidence) as avg_confidence
FROM predictions
GROUP BY DATE_TRUNC('day', created_at), model_id;

CREATE UNIQUE INDEX ON mv_daily_prediction_stats(date, model_id);
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_prediction_stats;
```

### 7.3 Connection Pooling

```yaml
PgBouncer Configuration:
  pool_mode: transaction
  max_client_conn: 10000
  default_pool_size: 25
  reserve_pool_size: 5
  reserve_pool_timeout: 3
  server_lifetime: 3600
  server_idle_timeout: 600
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
