# VLA Data Collection System - System Overview

## 3-Tier Architecture

The VLA Data Collection System is designed as a three-tier architecture optimized for robotics data collection, processing, and serving.

### Architectural Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION TIER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ REST API     │  │ WebSocket    │  │ Feedback UI  │  │ Dashboard  │ │
│  │ (FastAPI)    │  │ (Real-time)  │  │ (Forms)      │  │ (Grafana)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────────┘ │
└─────────┼───────────────────┼───────────────────┼─────────────────────────┘
          │                   │                   │
┌─────────┼───────────────────┼───────────────────┼─────────────────────────┐
│         │      BUSINESS LOGIC TIER              │                         │
│  ┌──────▼─────────────────────────────────────▼──────────┐               │
│  │              API Route Handlers                        │               │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐ │               │
│  │  │ Inference   │  │ Feedback     │  │ Data         │ │               │
│  │  │ Endpoints   │  │ Collection   │  │ Pipeline     │ │               │
│  │  └─────────────┘  └──────────────┘  └──────────────┘ │               │
│  └──────┬─────────────────────────────────────────────────┘               │
│         │                                                                 │
│  ┌──────▼─────────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                                   │  │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────┐  │  │
│  │  │ Inference Service    │  │ Data Pipeline Service            │  │  │
│  │  │  - Model Loading     │  │  - ETL Processing               │  │  │
│  │  │  - Batch Processing  │  │  - Data Validation              │  │  │
│  │  │  - Safety Checks     │  │  - Anonymization                │  │  │
│  │  └─────────┬────────────┘  │  - Embeddings Generation        │  │  │
│  │            │                │  - Storage Orchestration        │  │  │
│  │  ┌─────────▼──────────────┐ └──────────────────────────────────┘  │  │
│  │  │ Embeddings Service    │  ┌──────────────────────────────────┐  │  │
│  │  │  - Vector Generation  │  │ Storage Service                  │  │  │
│  │  │  - Similarity Search  │  │  - S3/MinIO Integration          │  │  │
│  │  │  - Index Maintenance  │  │  - Data Retention & Cleanup     │  │  │
│  │  └────────────────────────┘ └──────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
          │                   │                   │
┌─────────▼───────────────────▼───────────────────▼─────────────────────────┐
│                        DATA PERSISTENCE TIER                              │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────┐   │
│  │   PostgreSQL         │  │   Redis Cache       │  │   S3/MinIO     │   │
│  │  (Primary Database)  │  │  (Session & Queue)  │  │  (Object Store)│   │
│  │                      │  │                     │  │                │   │
│  │  ┌────────────────┐  │  │  ┌───────────────┐  │  │ ┌────────────┐ │   │
│  │  │ Inference Logs │  │  │  │ Rate Limiting │  │  │ │ Raw Data   │ │   │
│  │  │ Embeddings DB  │  │  │  │ Task Queue    │  │  │ │ Processed  │ │   │
│  │  │ Collections    │  │  │  │ Session State │  │  │ │ Embeddings │ │   │
│  │  │ Feedback       │  │  │  │               │  │  │ │ Audit Logs │ │   │
│  │  │ Audit Trail    │  │  │  │               │  │  │ └────────────┘ │   │
│  │  └────────────────┘  │  │  └───────────────┘  │  │                │   │
│  └──────────────────────┘  └─────────────────────┘  └────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Monitoring & Observability                                      │   │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐   │   │
│  │  │ Prometheus      │  │ Logs         │  │ Metrics           │   │   │
│  │  │ (Metrics)       │  │ (File-based) │  │ (GPU, API, DB)    │   │   │
│  │  └─────────────────┘  └──────────────┘  └───────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
```

## Tier Details

### 1. Presentation Tier (API Layer)

**Components:**
- REST API (FastAPI) - Primary interface for VLA inference and data submission
- WebSocket Connections - Real-time streaming and live monitoring
- Feedback UI - Forms for human-in-the-loop data collection
- Grafana Dashboard - Monitoring and metrics visualization

**Responsibilities:**
- Request routing and validation
- Authentication and authorization
- Rate limiting and quota enforcement
- Response formatting and error handling
- WebSocket connection management
- Metrics exposure (Prometheus)

**Key Endpoints:**
- `POST /api/v1/inference` - Submit robot state for inference
- `POST /api/v1/feedback` - Submit human feedback and corrections
- `GET /api/v1/collections` - List available data collections
- `WS /ws/inference` - Real-time inference stream
- `GET /metrics` - Prometheus metrics endpoint

---

### 2. Business Logic Tier (Service Layer)

**Components:**

#### 2.1 Inference Service
- Model loading and initialization
- Batch processing of inference requests
- Safety checks and constraint validation
- Result caching and optimization
- Timeout handling and circuit breaking

#### 2.2 Data Pipeline Service
- ETL (Extract, Transform, Load) orchestration
- Data validation and quality checks
- Anomaly detection
- Feature extraction
- Format standardization

#### 2.3 Embeddings Service
- Vector generation using sentence-transformers
- pgvector integration for similarity search
- Index maintenance and optimization
- Semantic search capabilities
- Dimensionality reduction if needed

#### 2.4 Storage Service
- S3/MinIO object storage integration
- Data lifecycle management
- Retention policy enforcement
- Encrypted storage handling
- Concurrent upload/download coordination

**Responsibilities:**
- Business logic implementation
- Data transformation and validation
- Cross-service orchestration
- State management
- Error handling and recovery
- Asynchronous task processing

**Key Patterns:**
- Service-to-service communication via dependency injection
- Async/await for I/O operations
- Queue-based processing for heavy workloads
- Caching layer for frequently accessed data

---

### 3. Data Persistence Tier

**Components:**

#### 3.1 PostgreSQL Database
Primary relational database for structured data:
- Inference metadata and results
- Embedding vectors (pgvector extension)
- Collection definitions and metadata
- User feedback and corrections
- Audit trail and compliance logs
- API keys and authentication tokens

**Key Tables:**
```sql
-- Inference Records
CREATE TABLE inference_results (
  id SERIAL PRIMARY KEY,
  request_id UUID UNIQUE,
  model_name VARCHAR(255),
  input_state JSONB,
  output_actions JSONB,
  safety_score FLOAT,
  inference_time_ms INT,
  created_at TIMESTAMP,
  collection_id INT REFERENCES collections(id)
);

-- Embeddings
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  collection_id INT REFERENCES collections(id),
  source_id UUID,
  embedding vector(384),
  metadata JSONB,
  created_at TIMESTAMP,
  INDEX embedding_idx USING ivfflat (embedding vector_cosine_ops)
);

-- Feedback Data
CREATE TABLE feedback (
  id SERIAL PRIMARY KEY,
  inference_result_id INT REFERENCES inference_results(id),
  feedback_type VARCHAR(50),
  human_correction JSONB,
  confidence FLOAT,
  created_at TIMESTAMP
);

-- Audit Trail
CREATE TABLE audit_logs (
  id SERIAL PRIMARY KEY,
  action VARCHAR(255),
  actor_id UUID,
  resource_type VARCHAR(100),
  resource_id UUID,
  changes JSONB,
  timestamp TIMESTAMP
);
```

#### 3.2 Redis Cache
Session and queue management:
- Rate limiting state (token bucket)
- Session tokens and JWT blacklist
- Task queue for data processing
- Temporary computation results
- Connection pooling

#### 3.3 S3/MinIO Object Storage
Unstructured data storage:
- Raw sensor data (images, point clouds)
- Processed datasets
- Generated embeddings (large exports)
- Audit logs and backups
- Model artifacts and versions

**Storage Structure:**
```
vla-data-collection/
├── raw/
│   ├── 2024-11-06/
│   │   ├── collection_1/
│   │   │   ├── inference_1.json
│   │   │   ├── image_1.png
│   │   │   └── ...
│   │   └── collection_2/
│   └── ...
├── processed/
│   ├── collection_1/
│   │   ├── batch_001.parquet
│   │   ├── validated_data.csv
│   │   └── ...
│   └── ...
├── embeddings/
│   ├── collection_1_embeddings.bin
│   └── ...
└── backups/
    ├── db_backup_2024-11-06.sql
    └── ...
```

#### 3.4 Monitoring Infrastructure
- Prometheus - Metrics collection and time-series database
- Grafana - Metrics visualization and alerting
- Log aggregation - Structured JSON logs
- GPU monitoring - NVIDIA GPU metrics

---

## Data Flow

### 1. Inference Request Flow
```
Client Request
    ↓
REST API Endpoint (/inference)
    ↓
Request Validation & Authentication
    ↓
Rate Limiting Check (Redis)
    ↓
Inference Service
    ├─ Safety Validation
    ├─ Model Inference
    └─ Result Post-processing
    ↓
Response Caching (Redis) [Optional]
    ↓
Database Logging (PostgreSQL)
    ↓
Metrics Recording (Prometheus)
    ↓
Client Response
```

### 2. Feedback Collection Flow
```
Feedback Submission
    ↓
REST API Endpoint (/feedback)
    ↓
Data Validation & Anonymization
    ↓
Database Storage (PostgreSQL)
    ↓
Embedding Generation (Embeddings Service)
    ├─ Vector Computation
    ├─ Vector Storage (pgvector)
    └─ Index Update
    ↓
Data Pipeline Queuing (Redis)
    ↓
Async Processing
    ├─ Data Enrichment
    ├─ Quality Checks
    └─ Object Storage (S3/MinIO)
    ↓
Metrics & Audit Logging
```

### 3. Data Pipeline Processing
```
Raw Data Source
    ↓
Data Validation Layer
    ├─ Schema Validation
    ├─ Type Checking
    └─ Anomaly Detection
    ↓
Anonymization Service
    ├─ PII Detection & Removal
    ├─ Hashing (SHA-256)
    └─ Audit Trail
    ↓
Feature Engineering
    ├─ Normalization
    ├─ Aggregation
    └─ Enrichment
    ↓
Embedding Generation
    ├─ Sentence-Transformers
    ├─ Vector Storage
    └─ Index Updates
    ↓
Object Storage
    ├─ Parquet Format
    ├─ Compression
    └─ S3/MinIO Upload
    ↓
Retention Management
    ├─ TTL Enforcement
    ├─ Archival
    └─ Deletion
```

---

## Scalability Considerations

### Horizontal Scaling

**API Tier:**
- Multiple FastAPI instances behind a load balancer
- Stateless design enables easy scaling
- Connection pooling for database connections

**Service Layer:**
- Async worker pools for background processing
- Task queue-based architecture (Celery alternative via Redis)
- Distributed embeddings computation

**Data Tier:**
- PostgreSQL read replicas for scaling reads
- Redis cluster for distributed caching
- S3/MinIO provides built-in distribution

### Performance Optimization

**Database:**
- Proper indexing on frequently queried columns
- Partitioning large tables by date (inference_results)
- Vector index optimization (IVFFlat configuration)
- Connection pooling with sqlalchemy

**Caching:**
- Redis for session and rate limit state
- Query result caching for embeddings
- HTTP caching headers for static responses

**Async Processing:**
- Non-blocking I/O for all database operations
- Batch processing for embeddings
- Queue-based data pipeline

---

## Security Architecture

### Authentication & Authorization
- API key validation for service-to-service communication
- JWT tokens for admin dashboard access
- Role-based access control (RBAC) for data collections

### Data Protection
- Encrypted storage for sensitive data (at-rest encryption)
- TLS/SSL for data in-transit
- PII anonymization in data pipeline
- Audit trail for compliance (SOC 2, HIPAA if needed)

### Rate Limiting
- Token bucket algorithm (Redis-backed)
- Per-API-key rate limits (configurable tiers)
- Burst allowance with backoff

---

## Deployment Topology

### Development
- Single machine: API, database, Redis, MinIO locally
- Docker Compose for easy setup
- Mock GPU inference for testing

### Staging
- Kubernetes cluster (3+ nodes)
- Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Managed Redis (ElastiCache, Cloud Memorystore)
- S3 or MinIO for object storage

### Production
- Kubernetes with auto-scaling
- Dedicated GPU nodes for inference
- Multi-region replication for databases
- CDN for static assets
- Backup and disaster recovery (PITR)

---

## Monitoring & Observability

### Key Metrics
- API request latency (p50, p95, p99)
- Model inference time
- GPU utilization and memory
- Database query performance
- Cache hit rates
- Rate limit violations
- Data pipeline throughput

### Logging Strategy
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing
- Centralized log aggregation

### Alerting
- High inference latency (>5s)
- GPU memory critical
- Database connection pool exhaustion
- Cache miss spike
- Error rate threshold (>1%)
- Data retention policy violations

---

## Technology Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| API Framework | FastAPI | 0.115.0 |
| ORM | SQLAlchemy | 2.0.36 |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7.0+ |
| Embeddings | Sentence-Transformers | 2.3.1 |
| Vector DB | pgvector | 0.2.4 |
| Object Storage | S3/MinIO | latest |
| Monitoring | Prometheus | 2.40+ |
| Visualization | Grafana | 9.0+ |
| Async | asyncio | 3.10+ |
| Image Processing | EasyOCR | 1.7.0 |
| Data Processing | Pandas | 2.2.0 |

---

## Future Enhancements

1. **Multi-Region Replication** - Geographic data distribution
2. **Real-time Analytics** - Streaming aggregations with Kafka
3. **Model Versioning** - A/B testing infrastructure
4. **Advanced Caching** - Predictive caching based on patterns
5. **Federated Learning** - Distributed model training
6. **Advanced Search** - Full-text search with Elasticsearch
7. **API Gateway** - Kong or similar for advanced routing
8. **Service Mesh** - Istio for traffic management and observability
