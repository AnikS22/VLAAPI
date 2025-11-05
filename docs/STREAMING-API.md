# 🎥 Live Streaming Inference API

Real-time VLA inference for continuous robot control at 10-50Hz.

## Overview

The streaming API enables **continuous inference** from live video streams for real-time robot control. Unlike single-shot inference, streaming maintains temporal context and provides action smoothing for stable control.

## Key Features

✅ **Real-Time Performance**: 10-50Hz inference rate
✅ **Action Smoothing**: Exponential moving average for stable control
✅ **Safety Monitoring**: Continuous safety evaluation
✅ **Low Latency**: <100ms end-to-end (target: 50ms)
✅ **Frame Buffering**: Automatic queue management
✅ **WebSocket Protocol**: Bi-directional streaming

## Quick Start

### 1. Install Dependencies

```bash
pip install websockets opencv-python numpy
```

### 2. Basic Example

```python
import asyncio
import cv2
from examples.streaming_client import VLAStreamingClient

async def main():
    # Create client
    client = VLAStreamingClient(
        api_url="ws://localhost:8000/v1/stream",
        api_key="vla_live_your_key_here"
    )

    # Connect
    await client.connect(
        model="openvla-7b",
        target_fps=10,
        enable_smoothing=True,
        enable_safety=True
    )

    # Open webcam
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Send frame
        await client.send_frame(
            image=frame,
            instruction="pick up the red cube"
        )

        # Receive action
        action_data = await client.receive_action()
        if action_data:
            action = action_data["action"]
            print(f"Action: {action}")

    await client.close()

asyncio.run(main())
```

## WebSocket Protocol

### Connection Flow

```
1. Client connects to ws://host:port/v1/stream
2. Client sends authentication message
3. Server creates streaming session
4. Client/Server exchange frames and actions
5. Client closes session
```

### Message Types

#### Client → Server

**Authentication**:
```json
{
  "type": "auth",
  "api_key": "vla_live_abc123...",
  "model": "openvla-7b",
  "robot_type": "franka_panda",
  "target_fps": 10,
  "enable_smoothing": true,
  "enable_safety": true
}
```

**Frame Submission**:
```json
{
  "type": "frame",
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "instruction": "pick up the red cube",
  "robot_state": {
    "pose": [0.3, 0.0, 0.5, 0.0, 0.0, 0.0],
    "velocity": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  }
}
```

**Request Statistics**:
```json
{
  "type": "stats"
}
```

**Close Session**:
```json
{
  "type": "close"
}
```

#### Server → Client

**Connection Confirmation**:
```json
{
  "type": "connected",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "config": {
    "model": "openvla-7b",
    "target_fps": 10,
    "smoothing": true,
    "safety": true
  }
}
```

**Action Response**:
```json
{
  "type": "action",
  "frame_id": 123,
  "timestamp": 1699564845.123,
  "action": [0.05, -0.02, 0.10, 0.0, 0.0, 0.1, 1.0],
  "safety_score": 0.95,
  "latency_ms": 45,
  "smoothed": true
}
```

**Statistics**:
```json
{
  "type": "stats",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "runtime_seconds": 120.5,
  "total_frames": 1200,
  "dropped_frames": 5,
  "drop_rate_percent": 0.42,
  "target_fps": 10,
  "actual_fps": 9.95,
  "avg_latency_ms": 42.3,
  "frame_queue_size": 2,
  "action_queue_size": 1
}
```

**Error**:
```json
{
  "type": "error",
  "message": "Frame queue full"
}
```

## Performance Tuning

### Target FPS Selection

| Application | Recommended FPS | Latency Budget |
|-------------|----------------|----------------|
| Pick & Place | 10 Hz | <100ms |
| Manipulation | 20 Hz | <50ms |
| Teleoperation | 30 Hz | <33ms |
| High-Speed Tasks | 50 Hz | <20ms |

### Action Smoothing

Smoothing reduces jitter but adds temporal lag:

```python
# More smoothing (stable, slower response)
await client.connect(
    target_fps=10,
    enable_smoothing=True,
    smoothing_alpha=0.2  # Lower = more smoothing
)

# Less smoothing (responsive, more jitter)
await client.connect(
    target_fps=20,
    enable_smoothing=True,
    smoothing_alpha=0.5  # Higher = less smoothing
)

# No smoothing (direct model output)
await client.connect(
    target_fps=30,
    enable_smoothing=False
)
```

### Frame Queue Management

**Problem**: Frames dropped when queue full
**Solution**: Reduce FPS or increase queue size

```python
# Adjust in server configuration (.env)
INFERENCE_QUEUE_MAX_SIZE=50  # Increase buffer
```

## Integration Examples

### Example 1: ROS Integration

```python
import rospy
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge

class ROSVLANode:
    def __init__(self):
        self.bridge = CvBridge()
        self.client = VLAStreamingClient(...)

        # Subscribe to camera
        rospy.Subscriber("/camera/image_raw", Image, self.image_callback)

        # Publish actions
        self.cmd_pub = rospy.Publisher("/robot/cmd_vel", Twist, queue_size=1)

    async def image_callback(self, msg):
        # Convert ROS image to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        # Send to VLA API
        await self.client.send_frame(
            image=frame,
            instruction=self.current_instruction
        )

        # Receive action
        action_data = await self.client.receive_action()
        if action_data:
            # Convert to ROS Twist
            cmd = Twist()
            cmd.linear.x = action_data["action"][0]
            cmd.linear.y = action_data["action"][1]
            self.cmd_pub.publish(cmd)
```

### Example 2: Physical Robot Control

```python
async def robot_control_loop():
    client = VLAStreamingClient(...)
    await client.connect(target_fps=20)

    # Initialize robot
    robot = RobotInterface()

    while robot.is_running():
        # Get camera frame
        frame = robot.get_camera_frame()

        # Get current state
        current_pose = robot.get_pose()
        current_velocity = robot.get_velocity()

        # Send to VLA
        await client.send_frame(
            image=frame,
            instruction=robot.get_current_task(),
            robot_state={
                "pose": current_pose,
                "velocity": current_velocity
            }
        )

        # Receive action
        action_data = await client.receive_action()

        if action_data:
            # Safety check passed on server
            if action_data["safety_score"] > 0.9:
                # Execute action
                robot.execute_delta_action(action_data["action"])
            else:
                # Low safety score - use emergency stop
                robot.emergency_stop()
                break

        # Maintain control frequency
        await asyncio.sleep(0.05)  # 20Hz
```

### Example 3: Teleoperation with VLA Assistance

```python
async def assisted_teleoperation():
    client = VLAStreamingClient(...)
    await client.connect()

    while True:
        # Get operator input
        operator_action = get_joystick_input()

        # Get VLA suggestion
        frame = get_camera_frame()
        await client.send_frame(frame, "assist operator")
        vla_action = await client.receive_action()

        # Blend actions (70% operator, 30% VLA)
        if vla_action:
            blended_action = (
                0.7 * operator_action +
                0.3 * np.array(vla_action["action"])
            )
            robot.execute_action(blended_action)
```

## Troubleshooting

### High Latency

**Symptom**: Latency > 200ms
**Solutions**:
- Reduce image resolution (640x480 → 320x240)
- Use faster model (π₀-FAST vs OpenVLA-7B)
- Disable safety checks temporarily
- Check network latency

### Dropped Frames

**Symptom**: drop_rate > 5%
**Solutions**:
- Reduce target FPS
- Increase queue size
- Optimize image encoding (JPEG quality)
- Check GPU utilization

### Inconsistent Actions

**Symptom**: Jittery robot movement
**Solutions**:
- Enable action smoothing
- Increase smoothing window
- Reduce FPS to allow more inference time
- Check instruction consistency

## API Reference

### VLAStreamingClient

```python
class VLAStreamingClient:
    async def connect(
        self,
        model: str = "openvla-7b",
        robot_type: str = "franka_panda",
        target_fps: int = 10,
        enable_smoothing: bool = True,
        enable_safety: bool = True
    )

    async def send_frame(
        self,
        image: np.ndarray,
        instruction: str,
        robot_state: dict = None
    )

    async def receive_action(
        self,
        timeout: float = 1.0
    ) -> dict

    async def get_stats() -> dict

    async def close()
```

## Rate Limits

Streaming sessions count toward your API quota:

| Tier | Max Concurrent Sessions | Max FPS per Session |
|------|------------------------|---------------------|
| Free | 1 | 10 Hz |
| Pro | 3 | 30 Hz |
| Enterprise | Unlimited | 50 Hz |

---

**Ready to stream?** Check out `examples/streaming_client.py` for complete examples!
