# Feedback API Documentation

## Overview

The Feedback API enables ground truth collection for VLA model improvement by allowing users to report success ratings, safety observations, action corrections, and failure reports for inference results.

## Endpoints

### 1. Report Success Rating

Report success/failure rating for an inference result.

**Endpoint:** `POST /v1/feedback/success`

**Request Body:**
```json
{
  "log_id": 12345,
  "rating": 5,
  "notes": "Perfect execution, robot completed task successfully"
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": 1,
  "log_id": 12345,
  "feedback_type": "success_rating",
  "customer_id": "uuid-here",
  "timestamp": "2025-01-15T10:30:00Z",
  "message": "Success rating 5/5 recorded successfully"
}
```

**Rating Scale:**
- 1: Complete failure
- 2: Mostly unsuccessful
- 3: Partially successful
- 4: Mostly successful
- 5: Perfect execution

---

### 2. Report Safety Rating

Report safety rating from human observation of robot execution.

**Endpoint:** `POST /v1/feedback/safety-rating`

**Request Body:**
```json
{
  "log_id": 12345,
  "rating": 4,
  "notes": "Robot maintained safe distance from obstacles"
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": 2,
  "log_id": 12345,
  "feedback_type": "safety_rating",
  "customer_id": "uuid-here",
  "timestamp": "2025-01-15T10:35:00Z",
  "message": "Safety rating 4/5 recorded successfully"
}
```

**Safety Rating Scale:**
- 1: Very unsafe (near miss or incident)
- 2: Concerning safety behavior
- 3: Acceptable with minor concerns
- 4: Safe with good margins
- 5: Perfectly safe execution

---

### 3. Report Action Correction

Report corrected 7-DoF action vector when model prediction was incorrect.

**Endpoint:** `POST /v1/feedback/action-correction`

**Request Body:**
```json
{
  "log_id": 12345,
  "corrected_action": [0.05, 0.02, -0.01, 0.0, 0.0, 0.1, 1.0],
  "notes": "Adjusted z-axis to avoid collision with table"
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": 3,
  "log_id": 12345,
  "feedback_type": "action_correction",
  "customer_id": "uuid-here",
  "timestamp": "2025-01-15T10:40:00Z",
  "message": "Action correction recorded (magnitude: 0.1234)"
}
```

**Action Vector Format:**
- 7-DoF: `[dx, dy, dz, droll, dpitch, dyaw, gripper]`
- First 3 components: translation (meters)
- Next 3 components: rotation (radians)
- Last component: gripper (0.0 = closed, 1.0 = open)

---

### 4. Report Failure

Report why inference failed in real robot execution.

**Endpoint:** `POST /v1/feedback/failure-report`

**Request Body:**
```json
{
  "log_id": 12345,
  "failure_reason": "collision",
  "notes": "Robot collided with table edge during execution"
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": 4,
  "log_id": 12345,
  "feedback_type": "failure_report",
  "customer_id": "uuid-here",
  "timestamp": "2025-01-15T10:45:00Z",
  "message": "Failure report recorded: collision"
}
```

**Common Failure Reasons:**
- `collision` - Robot collided with object
- `gripper_malfunction` - Gripper failed to operate
- `wrong_object` - Robot picked up wrong object
- `incomplete_task` - Task not completed
- `timeout` - Task timed out
- `out_of_reach` - Target out of workspace
- `safety_stop` - Safety system triggered

---

### 5. Get Feedback Statistics

Retrieve comprehensive feedback statistics for your account.

**Endpoint:** `GET /v1/feedback/stats`

**Response:** `200 OK`
```json
{
  "customer_id": "uuid-here",
  "total_feedback_count": 150,
  "total_inference_count": 1000,
  "feedback_rate": 0.15,
  "feedback_by_type": {
    "success_rating": 80,
    "safety_rating": 40,
    "action_correction": 20,
    "failure_report": 10
  },
  "average_success_rating": 4.2,
  "average_safety_rating": 4.5,
  "correction_count": 20,
  "average_correction_magnitude": 0.087,
  "failure_count": 10,
  "top_failure_reasons": [
    {"reason": "collision", "count": 5},
    {"reason": "gripper_malfunction", "count": 3},
    {"reason": "timeout", "count": 2}
  ],
  "period": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-31T23:59:59Z"
  }
}
```

**Metrics Explained:**
- `feedback_rate`: Percentage of inferences with feedback (0.0-1.0)
- `average_success_rating`: Mean success rating (1.0-5.0)
- `average_safety_rating`: Mean safety rating (1.0-5.0)
- `average_correction_magnitude`: Mean L2 norm of action corrections
- `top_failure_reasons`: Most common failure reasons with counts

---

### 6. List Feedback

Get paginated list of feedback submissions with optional filtering.

**Endpoint:** `GET /v1/feedback/list`

**Query Parameters:**
- `page` (optional): Page number, default 1
- `per_page` (optional): Items per page, default 50, max 200
- `feedback_type` (optional): Filter by type (success_rating, safety_rating, action_correction, failure_report)

**Example Request:**
```
GET /v1/feedback/list?page=1&per_page=20&feedback_type=action_correction
```

**Response:** `200 OK`
```json
{
  "feedback": [
    {
      "feedback_id": 3,
      "log_id": 12345,
      "feedback_type": "action_correction",
      "customer_id": "uuid-here",
      "timestamp": "2025-01-15T10:40:00Z",
      "rating": null,
      "corrected_action": [0.05, 0.02, -0.01, 0.0, 0.0, 0.1, 1.0],
      "original_action": [0.08, 0.03, 0.01, 0.0, 0.0, 0.08, 1.0],
      "correction_delta": [-0.03, -0.01, -0.02, 0.0, 0.0, 0.02, 0.0],
      "correction_magnitude": 0.0412,
      "failure_reason": null,
      "notes": "Adjusted z-axis to avoid collision"
    }
  ],
  "total_count": 20,
  "page": 1,
  "per_page": 20,
  "has_next": false
}
```

---

## Authentication

All endpoints require authentication via Bearer token:

```bash
curl -X POST https://api.vlaapi.com/v1/feedback/success \
  -H "Authorization: Bearer vla_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"log_id": 12345, "rating": 5}'
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "validation_error",
  "message": "Invalid request data",
  "details": {
    "corrected_action": "Action component 2 must be finite (got nan)"
  }
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "Invalid or missing API key"
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "Inference log 12345 not found or doesn't belong to customer"
}
```

### 422 Unprocessable Entity
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "validation_errors": [
    {
      "loc": ["body", "rating"],
      "msg": "Rating must be between 1 and 5",
      "type": "value_error"
    }
  ]
}
```

---

## Use Cases

### 1. Supervised Learning Pipeline

Collect action corrections to train/fine-tune VLA models:

```python
# After robot execution, if action was incorrect
corrected_action = human_operator.get_corrected_action()

response = requests.post(
    "https://api.vlaapi.com/v1/feedback/action-correction",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "log_id": inference_log_id,
        "corrected_action": corrected_action,
        "notes": "Human correction for training data"
    }
)
```

### 2. Safety Model Training

Collect human safety ratings to improve safety classifiers:

```python
# Human observer rates safety
safety_rating = observer.rate_safety(execution_video)

response = requests.post(
    "https://api.vlaapi.com/v1/feedback/safety-rating",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "log_id": inference_log_id,
        "rating": safety_rating,
        "notes": observer.notes
    }
)
```

### 3. Failure Analysis

Track failure patterns to identify systematic issues:

```python
# After execution failure
if execution_failed:
    response = requests.post(
        "https://api.vlaapi.com/v1/feedback/failure-report",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "log_id": inference_log_id,
            "failure_reason": failure_classifier.classify(),
            "notes": failure_details
        }
    )
```

### 4. Model Performance Monitoring

Track success rates over time:

```python
# Get statistics
response = requests.get(
    "https://api.vlaapi.com/v1/feedback/stats",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

stats = response.json()
success_rate = stats["average_success_rating"]
feedback_rate = stats["feedback_rate"]

# Alert if performance degrades
if success_rate < 3.5:
    alert_team("Model performance below threshold")
```

---

## Best Practices

1. **Feedback Timing**: Submit feedback as soon as possible after execution
2. **Quality Over Quantity**: Focus on providing accurate, detailed feedback
3. **Action Corrections**: Ensure corrected actions are validated before submission
4. **Notes Field**: Use notes to provide context that helps model training
5. **Failure Reasons**: Use consistent, descriptive failure reason strings
6. **Monitoring**: Regularly check feedback stats to track data quality

---

## Rate Limits

Feedback endpoints share the same rate limits as inference endpoints:

- Free tier: 60 requests/minute
- Pro tier: 300 requests/minute
- Enterprise tier: Custom limits

---

## Data Privacy

- Feedback data is stored securely and associated with your account
- Feedback can be used for model improvement (with appropriate consent)
- Data retention follows your subscription tier's policy
- Export feedback data via API or dashboard

---

## Support

For questions about the Feedback API:
- Email: support@vlaapi.com
- Documentation: https://docs.vlaapi.com/feedback
- API Status: https://status.vlaapi.com
