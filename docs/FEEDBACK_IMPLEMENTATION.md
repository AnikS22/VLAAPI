# Feedback API Implementation

## Overview

The Feedback API has been successfully implemented for ground truth collection. This system enables customers to provide feedback on inference results, which is critical for:

1. **Model Improvement**: Collecting action corrections for supervised learning
2. **Safety Enhancement**: Gathering human safety ratings to improve safety classifiers
3. **Failure Analysis**: Tracking failure patterns to identify systematic issues
4. **Quality Monitoring**: Measuring model performance through success ratings

---

## Implementation Summary

### Files Created

#### 1. Contract Models (`/src/models/contracts/feedback.py`)
- **FeedbackType** enum: success_rating, safety_rating, action_correction, failure_report
- **Request Models**:
  - `SuccessRatingRequest`
  - `SafetyRatingRequest`
  - `ActionCorrectionRequest`
  - `FailureReportRequest`
- **Response Models**:
  - `FeedbackResponse`
  - `FeedbackStatsResponse`
  - `FeedbackDetailResponse`
  - `FeedbackListResponse`

#### 2. Database Models (`/src/models/database.py`)
- **Feedback** table with fields:
  - Primary key: `feedback_id`
  - Foreign keys: `log_id`, `customer_id`
  - Type-specific fields: `rating`, `corrected_action`, `failure_reason`
  - Computed fields: `correction_delta`, `correction_magnitude`
  - Indexed by: customer, log, type, timestamp

#### 3. Service Layer (`/src/services/feedback/feedback_service.py`)
- **FeedbackService** class with methods:
  - `create_success_rating()`: Record success ratings
  - `create_safety_rating()`: Record safety ratings
  - `create_action_correction()`: Record action corrections with delta calculation
  - `create_failure_report()`: Record failure reports
  - `get_feedback_stats()`: Aggregate statistics
  - `get_feedback_list()`: Paginated feedback listing

#### 4. API Router (`/src/api/routers/feedback/feedback.py`)
- **Endpoints**:
  - `POST /v1/feedback/success`: Report success rating (1-5 stars)
  - `POST /v1/feedback/safety-rating`: Report safety rating (1-5 stars)
  - `POST /v1/feedback/action-correction`: Report corrected 7-DoF action
  - `POST /v1/feedback/failure-report`: Report failure reason
  - `GET /v1/feedback/stats`: Get feedback statistics
  - `GET /v1/feedback/list`: List feedback with pagination and filtering

#### 5. Database Migration (`/migrations/003_add_feedback_table.sql`)
- Creates `feedback` table with proper constraints
- Creates indexes for query performance
- Creates `feedback_analytics` materialized view for aggregated stats
- Includes rollback script (`004_rollback_feedback.sql`)

#### 6. Tests (`/tests/api/test_feedback.py`)
- Comprehensive test suite covering:
  - Success rating validation
  - Safety rating validation
  - Action correction validation (dimensions, finite values, gripper range)
  - Failure report validation
  - Statistics endpoint
  - List endpoint with pagination and filtering
  - Authentication and authorization

#### 7. Documentation (`/docs/feedback_api.md`)
- Complete API documentation with:
  - Endpoint descriptions
  - Request/response examples
  - Rating scales and action vector formats
  - Error responses
  - Use cases and best practices

---

## Database Schema

```sql
CREATE TABLE vlaapi.feedback (
    feedback_id SERIAL PRIMARY KEY,
    log_id INTEGER NOT NULL REFERENCES vlaapi.inference_logs(log_id),
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id),

    -- Feedback metadata
    feedback_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Type-specific fields
    rating INTEGER,                    -- For success/safety ratings (1-5)
    corrected_action FLOAT[],          -- For action corrections (7-DoF)
    original_action FLOAT[],           -- Original action from inference
    correction_delta FLOAT[],          -- corrected - original
    correction_magnitude FLOAT,        -- L2 norm of delta
    failure_reason VARCHAR(200),       -- For failure reports
    notes TEXT,                        -- Optional notes

    CONSTRAINT chk_feedback_type CHECK (
        feedback_type IN ('success_rating', 'safety_rating', 'action_correction', 'failure_report')
    ),
    CONSTRAINT chk_rating_range CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5))
);

-- Indexes
CREATE INDEX idx_feedback_customer ON vlaapi.feedback(customer_id);
CREATE INDEX idx_feedback_log ON vlaapi.feedback(log_id);
CREATE INDEX idx_feedback_type ON vlaapi.feedback(feedback_type);
CREATE INDEX idx_feedback_timestamp ON vlaapi.feedback USING btree (timestamp DESC);
```

---

## API Usage Examples

### 1. Report Success Rating

```bash
curl -X POST https://api.vlaapi.com/v1/feedback/success \
  -H "Authorization: Bearer vla_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 12345,
    "rating": 5,
    "notes": "Perfect execution, robot completed task successfully"
  }'
```

### 2. Report Safety Rating

```bash
curl -X POST https://api.vlaapi.com/v1/feedback/safety-rating \
  -H "Authorization: Bearer vla_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 12345,
    "rating": 4,
    "notes": "Robot maintained safe distance from obstacles"
  }'
```

### 3. Report Action Correction

```bash
curl -X POST https://api.vlaapi.com/v1/feedback/action-correction \
  -H "Authorization: Bearer vla_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 12345,
    "corrected_action": [0.05, 0.02, -0.01, 0.0, 0.0, 0.1, 1.0],
    "notes": "Adjusted z-axis to avoid collision"
  }'
```

### 4. Report Failure

```bash
curl -X POST https://api.vlaapi.com/v1/feedback/failure-report \
  -H "Authorization: Bearer vla_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 12345,
    "failure_reason": "collision",
    "notes": "Robot collided with table edge"
  }'
```

### 5. Get Statistics

```bash
curl -X GET https://api.vlaapi.com/v1/feedback/stats \
  -H "Authorization: Bearer vla_live_abc123..."
```

---

## Validation Rules

### Success/Safety Ratings
- **Rating**: Must be integer 1-5
- **Log ID**: Must exist and belong to customer
- **Notes**: Optional, max 1000 characters

### Action Corrections
- **Corrected Action**: Must be exactly 7 dimensions
- **Values**: All must be finite (no NaN, Inf, -Inf)
- **Gripper**: Must be in range [0.0, 1.0]
- **Magnitude**: Automatically calculated as L2 norm of delta

### Failure Reports
- **Failure Reason**: Required, max 200 characters
- **Notes**: Optional, max 1000 characters

---

## Analytics Features

### Feedback Statistics
- Total feedback count by type
- Feedback rate (feedback/total inferences)
- Average success rating (1-5)
- Average safety rating (1-5)
- Average correction magnitude
- Top failure reasons with counts

### Materialized View
The `feedback_analytics` materialized view provides daily aggregated statistics:
- Feedback counts by type per day
- Average ratings per day
- Average correction magnitude per day
- Per customer aggregation

**Refresh Strategy:**
```sql
-- Refresh materialized view (run periodically via cron)
REFRESH MATERIALIZED VIEW vlaapi.feedback_analytics;
```

---

## Integration Steps

### 1. Run Database Migration

```bash
# Apply migration
psql -U postgres -d vlaapi -f migrations/003_add_feedback_table.sql

# Verify table creation
psql -U postgres -d vlaapi -c "\d vlaapi.feedback"
```

### 2. Update Application

The feedback router has been added to the main application:
```python
# In src/api/main.py
from src.api.routers.feedback import router as feedback_router
app.include_router(feedback_router)
```

### 3. Test Endpoints

```bash
# Run tests
pytest tests/api/test_feedback.py -v

# Test specific endpoint
pytest tests/api/test_feedback.py::TestSuccessRating::test_report_success_rating_valid -v
```

### 4. Monitor Usage

```bash
# Check feedback stats
curl https://api.vlaapi.com/v1/feedback/stats -H "Authorization: Bearer $API_KEY"

# List recent feedback
curl "https://api.vlaapi.com/v1/feedback/list?page=1&per_page=10" \
  -H "Authorization: Bearer $API_KEY"
```

---

## Performance Considerations

### Indexes
- Customer ID: Fast lookup of customer's feedback
- Log ID: Fast lookup of feedback for specific inference
- Type: Fast filtering by feedback type
- Timestamp: Fast ordering and time-range queries

### Materialized View
- Pre-aggregated statistics for dashboard queries
- Refresh strategy: Daily or hourly depending on load
- Significantly faster than real-time aggregation

### Query Optimization
- Pagination for large result sets
- Optional filtering to reduce data transfer
- Efficient aggregate queries using materialized view

---

## Security Considerations

### Authorization
- All endpoints require valid API key
- Feedback can only be submitted for customer's own inference logs
- Cross-customer access prevented by ownership verification

### Input Validation
- All inputs validated by Pydantic models
- Action vectors validated for finite values
- Rating ranges enforced (1-5)
- Maximum lengths for text fields

### Rate Limiting
- Feedback endpoints share rate limits with inference endpoints
- Prevents abuse and ensures fair usage

---

## Future Enhancements

### Phase 2: Advanced Analytics
1. **Trend Analysis**: Track rating trends over time
2. **Anomaly Detection**: Identify unusual failure patterns
3. **Correlation Analysis**: Link feedback to context metadata
4. **Predictive Models**: Predict likelihood of failure based on context

### Phase 3: ML Integration
1. **Automated Retraining**: Trigger model retraining when correction threshold met
2. **Active Learning**: Prioritize samples for human feedback
3. **Feedback Loop**: Use corrections for online learning
4. **A/B Testing**: Compare models using feedback metrics

### Phase 4: Dashboard Integration
1. **Visualization**: Charts and graphs of feedback trends
2. **Alerts**: Notify when performance degrades
3. **Exports**: Download feedback data for analysis
4. **Insights**: Automated insights from feedback patterns

---

## Troubleshooting

### Common Issues

1. **404 Not Found**: Log ID doesn't exist or belongs to different customer
   - Verify log_id exists in inference_logs table
   - Check customer_id matches

2. **422 Validation Error**: Invalid input format
   - Check rating is 1-5
   - Verify action vector has exactly 7 dimensions
   - Ensure all values are finite

3. **401 Unauthorized**: Invalid or missing API key
   - Verify API key is valid
   - Check Authorization header format

### Debug Queries

```sql
-- Check feedback for specific log
SELECT * FROM vlaapi.feedback WHERE log_id = 12345;

-- Check feedback statistics for customer
SELECT
    feedback_type,
    COUNT(*) as count,
    AVG(rating) as avg_rating
FROM vlaapi.feedback
WHERE customer_id = 'uuid-here'
GROUP BY feedback_type;

-- Check correction magnitudes
SELECT
    AVG(correction_magnitude) as avg_magnitude,
    MIN(correction_magnitude) as min_magnitude,
    MAX(correction_magnitude) as max_magnitude
FROM vlaapi.feedback
WHERE feedback_type = 'action_correction';
```

---

## Conclusion

The Feedback API is now fully implemented and ready for production use. It provides:

✅ **4 feedback types**: Success, safety, corrections, failures
✅ **Complete validation**: Pydantic models with comprehensive checks
✅ **Database schema**: Indexed table with materialized view for analytics
✅ **Service layer**: Business logic for feedback processing
✅ **REST API**: 6 endpoints with full documentation
✅ **Tests**: Comprehensive test suite for all endpoints
✅ **Documentation**: Complete API documentation with examples

This implementation provides a solid foundation for ground truth collection and will enable continuous model improvement through customer feedback.

---

## Related Documentation

- [API Documentation](./feedback_api.md)
- [Database Schema](../migrations/003_add_feedback_table.sql)
- [Test Suite](../tests/api/test_feedback.py)
- [Service Layer](../src/services/feedback/feedback_service.py)
- [API Router](../src/api/routers/feedback/feedback.py)
