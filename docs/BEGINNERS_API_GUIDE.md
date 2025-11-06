# 🎓 Beginner's Guide to APIs and the VLA Inference API

## 📚 Part 1: What is an API? (For Complete Beginners)

### The Restaurant Analogy

Imagine you're at a restaurant:

1. **You (Customer)** = Your application or script
2. **Menu** = API documentation (what you can order)
3. **Waiter** = The API (takes your order and brings results)
4. **Kitchen** = The server (does the actual work)
5. **Your Food** = The response (data you requested)

**How it works:**
- You look at the menu and say: "I want a burger with fries"
- The waiter writes it down and takes it to the kitchen
- The kitchen makes your food
- The waiter brings it back to you

**In programming terms:**
- You read the API docs and make a request: "I want robot action for this image"
- The API receives your request (HTTP POST)
- The server processes it (runs AI model on GPU)
- The API sends back the result (7-DoF action vector)

---

## 🌐 Part 2: How HTTP APIs Work

### Request-Response Cycle

```
YOUR COMPUTER                    API SERVER
     |                                |
     |  1. Send Request (POST)        |
     |  "Here's an image + text"      |
     |------------------------------->|
     |                                |
     |                          2. Process
     |                          (Run AI model)
     |                                |
     |  3. Send Response              |
     |  "Here's the robot action"     |
     |<-------------------------------|
     |                                |
```

### Key Concepts

**1. URL (Address)**
- Like a house address, but for a server
- Example: `http://localhost:8000/v1/inference`
- Parts:
  - `http://` = protocol (how to talk)
  - `localhost:8000` = server location and port
  - `/v1/inference` = specific endpoint (what you want)

**2. HTTP Methods**
- `GET` = "Give me data" (like viewing a menu)
- `POST` = "Here's data, do something with it" (like ordering food)
- `PUT` = "Update this data"
- `DELETE` = "Remove this data"

**3. Headers**
- Extra information about your request
- `Authorization: Bearer YOUR_API_KEY` = proves you're allowed to use the API
- `Content-Type: application/json` = tells server the data format

**4. Body**
- The actual data you're sending
- For VLA API: image (base64) + instruction (text)

**5. Response**
- What the server sends back
- Includes:
  - Status code (200 = success, 404 = not found, 500 = server error)
  - Response body (the data you wanted)

---

## 🚀 Part 3: Getting the VLA API Running

### Prerequisites (Check These First)

```bash
# 1. Check Python version (need 3.10+)
python3 --version

# 2. Check if Docker is installed (for database)
docker --version

# 3. Check if you have a GPU (optional, for production)
nvidia-smi
```

### Step-by-Step Installation

#### Step 1: Set Up Python Environment

```bash
# Navigate to the project directory
cd /Users/aniksahai/Desktop/VLAAPI

# Create a virtual environment (isolated Python installation)
python3.10 -m venv venv

# Activate it
source venv/bin/activate  # On Mac/Linux
# OR
venv\Scripts\activate  # On Windows

# Your terminal should now show (venv) at the start
```

#### Step 2: Install Dependencies

```bash
# Install all required Python packages
pip install -r requirements.txt

# This will take a few minutes (installing ~30 packages)
```

#### Step 3: Set Up Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the file (use nano, vim, or any text editor)
nano .env
```

**Important settings to change in .env:**
```bash
# For testing WITHOUT GPU (easier to start)
USE_MOCK_MODELS=true

# Database connection (using Docker)
DATABASE_URL=postgresql+asyncpg://vlaapi:password@localhost:5432/vlaapi

# Redis cache
REDIS_URL=redis://localhost:6379/0

# Enable monitoring
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=false  # Set to false if no GPU
```

#### Step 4: Start Database & Redis

```bash
# Start PostgreSQL and Redis using Docker
docker-compose up -d postgres redis

# Check they're running
docker-compose ps

# Should show:
# vlaapi-postgres    Up
# vlaapi-redis       Up
```

#### Step 5: Initialize Database

```bash
# Create the database schema
python scripts/setup_database.py

# When prompted, answer 'y' to seed demo data
# This creates a test API key - SAVE THIS KEY!
```

You should see output like:
```
✅ Database initialized successfully!
🔑 Demo API key created: vla_live_abc123def456...
💾 Save this key - you'll need it for testing!
```

#### Step 6: Start the API Server

```bash
# Start the server with mock models (no GPU needed)
USE_MOCK_MODELS=true python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

**🎉 Congratulations! Your API is now running!**

---

## 🧪 Part 4: Testing Your API

### Test 1: Health Check (Simplest Test)

Open a **new terminal** (keep the server running in the first one):

```bash
# Simple test - is the server alive?
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}
```

### Test 2: View API Documentation

Open your web browser and go to:
```
http://localhost:8000/docs
```

This shows **interactive API documentation** where you can:
- See all available endpoints
- See what data each endpoint expects
- Try making requests directly from the browser

### Test 3: Make Your First Inference Request

#### Using curl (Command Line)

```bash
# Replace YOUR_API_KEY with the key from setup
curl -X POST http://localhost:8000/v1/inference \
  -H "Authorization: Bearer vla_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }'
```

**Expected response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1704067200.0,
  "model": "openvla-7b",
  "action": {
    "type": "end_effector_delta",
    "dimensions": 7,
    "values": [0.15, -0.08, 0.22, 0.01, 0.05, -0.03, 1.0]
  },
  "safety": {
    "overall_score": 0.92,
    "checks_passed": 4,
    "flags": []
  },
  "performance": {
    "total_latency_ms": 145,
    "queue_wait_ms": 5,
    "inference_ms": 120
  }
}
```

---

## 🐍 Part 5: Using the API from Python

### Example 1: Simple Inference Request

Create a file called `test_api.py`:

```python
#!/usr/bin/env python3
"""Simple test of VLA Inference API."""

import requests
import base64

# Configuration
API_URL = "http://localhost:8000/v1/inference"
API_KEY = "vla_live_YOUR_KEY_HERE"  # Replace with your actual key

# Prepare request
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# For testing, use a small 1x1 pixel image
# In real use, you'd load an actual image from a camera
test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

data = {
    "model": "openvla-7b",
    "image": test_image_base64,
    "instruction": "pick up the red cube",
    "robot_config": {
        "type": "franka_panda"
    }
}

# Make request
print("Sending request to API...")
response = requests.post(API_URL, headers=headers, json=data)

# Check if successful
if response.status_code == 200:
    result = response.json()
    print("\n✅ Success!")
    print(f"Request ID: {result['request_id']}")
    print(f"Robot Action: {result['action']['values']}")
    print(f"Safety Score: {result['safety']['overall_score']}")
    print(f"Latency: {result['performance']['total_latency_ms']}ms")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
```

Run it:
```bash
python test_api.py
```

### Example 2: Using a Real Image

```python
#!/usr/bin/env python3
"""Test VLA API with a real image."""

import requests
import base64
from pathlib import Path

API_URL = "http://localhost:8000/v1/inference"
API_KEY = "vla_live_YOUR_KEY_HERE"

def encode_image(image_path):
    """Read and encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# Load your image
image_path = "robot_camera.jpg"  # Replace with your image
image_base64 = encode_image(image_path)

# Make request
response = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "openvla-7b",
        "image": image_base64,
        "instruction": "grasp the object in front of you"
    }
)

if response.status_code == 200:
    action = response.json()["action"]["values"]
    print(f"Robot should move to: {action}")
else:
    print(f"Error: {response.text}")
```

### Example 3: Real Robot Integration Loop

```python
#!/usr/bin/env python3
"""Continuous robot control loop."""

import requests
import base64
import time

API_URL = "http://localhost:8000/v1/inference"
API_KEY = "vla_live_YOUR_KEY_HERE"

def get_robot_camera_image():
    """Get image from robot camera (placeholder)."""
    # In real robot, this would be:
    # return robot.get_camera_frame()
    
    # For testing, load from file
    with open("camera_feed.jpg", "rb") as f:
        return base64.b64encode(f.read()).decode()

def send_action_to_robot(action):
    """Send action to robot (placeholder)."""
    # In real robot, this would be:
    # robot.execute_action(action)
    print(f"Executing action: {action}")

# Main control loop
print("Starting robot control loop...")
print("Press Ctrl+C to stop")

try:
    while True:
        # 1. Get current image
        image = get_robot_camera_image()
        
        # 2. Get action from VLA API
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": "openvla-7b",
                "image": image,
                "instruction": "pick up the red object"
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            result = response.json()
            action = result["action"]["values"]
            safety_score = result["safety"]["overall_score"]
            
            # 3. Check safety
            if safety_score >= 0.8:
                send_action_to_robot(action)
                print(f"✓ Action executed (safety: {safety_score:.2f})")
            else:
                print(f"⚠ Action rejected (unsafe: {safety_score:.2f})")
        else:
            print(f"✗ API error: {response.status_code}")
        
        # 4. Wait before next iteration (10Hz control loop)
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping control loop...")
```

---

## 🔍 Part 6: Understanding the Response

### What Do the Numbers Mean?

When you get a response like:
```json
"action": {
  "values": [0.15, -0.08, 0.22, 0.01, 0.05, -0.03, 1.0]
}
```

These are **7-DoF (Degrees of Freedom)** robot movements:

1. **Position (XYZ)**: First 3 numbers = where to move in space
   - `0.15` = Move +15cm in X direction (forward/back)
   - `-0.08` = Move -8cm in Y direction (left/right)
   - `0.22` = Move +22cm in Z direction (up/down)

2. **Orientation (Roll/Pitch/Yaw)**: Next 3 numbers = how to rotate
   - `0.01` = Slight roll rotation
   - `0.05` = Slight pitch rotation
   - `-0.03` = Slight yaw rotation

3. **Gripper**: Last number = open/close gripper
   - `1.0` = Fully closed (grasping)
   - `0.0` = Fully open (releasing)
   - `0.5` = Half-way (soft grasp)

### Safety Score

```json
"safety": {
  "overall_score": 0.92
}
```

- **0.92 (92%)** = Very safe action
- **0.70-0.79** = Moderately safe (might get modified)
- **Below 0.70** = Unsafe (rejected)

### Performance Metrics

```json
"performance": {
  "total_latency_ms": 145,
  "queue_wait_ms": 5,
  "inference_ms": 120
}
```

- **145ms total** = Time from request to response
- **5ms queue** = Time waiting in line
- **120ms inference** = Time for AI to compute action

---

## 🐛 Part 7: Common Problems & Solutions

### Problem 1: "Connection refused"

**Error:**
```
curl: (7) Failed to connect to localhost port 8000
```

**Solution:**
- Make sure the API server is running
- Check: Is `python -m uvicorn src.api.main:app` still running?
- Try restarting it

### Problem 2: "Unauthorized" (401 error)

**Error:**
```json
{"error": "unauthorized", "message": "Invalid API key"}
```

**Solution:**
- Check your API key is correct
- Make sure header is: `Authorization: Bearer vla_live_...`
- Re-run `python scripts/setup_database.py` to create new key

### Problem 3: "Model not loaded"

**Error:**
```json
{"error": "Model openvla-7b is not loaded"}
```

**Solution:**
- Make sure you set `USE_MOCK_MODELS=true` in .env
- Or if using real models, wait for model to download (first time only)

### Problem 4: "Database connection failed"

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check Docker containers are running
docker-compose ps

# If not running, start them
docker-compose up -d postgres redis

# Check logs for errors
docker-compose logs postgres
```

---

## 📖 Part 8: Next Steps

### For Learning More:

1. **Interactive Documentation**
   - Go to: `http://localhost:8000/docs`
   - Try different endpoints directly in browser

2. **WebSocket Streaming** (Advanced)
   - See: `examples/streaming_client.py`
   - For real-time robot control at 10-50Hz

3. **Monitoring Dashboard**
   - Start Grafana: `docker-compose --profile monitoring up -d`
   - View at: `http://localhost:3000`
   - See real-time metrics and performance

4. **Full Documentation**
   - API Reference: `docs/VLA-API-README.md`
   - System Report: `docs/COMPLETE_SYSTEM_REPORT.md`

### For Production Use:

1. **Enable Real Models** (requires GPU)
   ```bash
   # Edit .env
   USE_MOCK_MODELS=false
   ENABLED_MODELS=openvla-7b
   ```

2. **Add Your Robot Configuration**
   ```yaml
   # config/robot_configs/my_robot.yaml
   name: "My Robot"
   dof: 7
   workspace_bounds: [[-0.6, -0.6, 0.0], [0.6, 0.6, 0.8]]
   ```

3. **Add Your Safety Checks**
   ```python
   # src/services/custom_alignment.py
   # Implement your alignment research
   ```

---

## 💡 Quick Reference Card

### Start Everything
```bash
# 1. Activate Python environment
source venv/bin/activate

# 2. Start database
docker-compose up -d postgres redis

# 3. Start API
USE_MOCK_MODELS=true python -m uvicorn src.api.main:app --port 8000
```

### Test Health
```bash
curl http://localhost:8000/health
```

### Make Inference Request
```python
import requests

response = requests.post(
    "http://localhost:8000/v1/inference",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "model": "openvla-7b",
        "image": "BASE64_IMAGE_HERE",
        "instruction": "pick up the object"
    }
)

action = response.json()["action"]["values"]
```

### Stop Everything
```bash
# Stop API: Press Ctrl+C in terminal

# Stop database
docker-compose down
```

---

## 🎓 Summary

**You learned:**
- ✅ What APIs are and how they work
- ✅ How to install and configure the VLA API
- ✅ How to make API requests from command line and Python
- ✅ How to interpret robot actions and safety scores
- ✅ How to troubleshoot common problems
- ✅ How to integrate with real robots

**You can now:**
- Send images + instructions to the API
- Receive robot actions in return
- Build robot control applications
- Understand API responses
- Debug issues when they occur

---

## 🆘 Getting Help

- **Documentation**: Check `docs/` folder
- **Examples**: See `examples/` folder
- **Logs**: Check terminal output where server is running
- **Interactive Docs**: `http://localhost:8000/docs`

**Remember:** APIs are just a way for programs to talk to each other. You send data, the API processes it, and sends back results. That's it! 🚀

