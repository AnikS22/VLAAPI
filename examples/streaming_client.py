#!/usr/bin/env python3
"""Example client for live streaming VLA inference.

This demonstrates how to use the WebSocket streaming API for real-time
robot control at 10-50Hz.
"""

import asyncio
import base64
import json
import time
from pathlib import Path

import cv2
import numpy as np
import websockets


class VLAStreamingClient:
    """Client for streaming VLA inference."""

    def __init__(self, api_url: str, api_key: str):
        """Initialize streaming client.

        Args:
            api_url: WebSocket URL (e.g., ws://localhost:8000/v1/stream)
            api_key: API key for authentication
        """
        self.api_url = api_url
        self.api_key = api_key
        self.websocket = None
        self.session_id = None
        self.is_connected = False

    async def connect(
        self,
        model: str = "openvla-7b",
        robot_type: str = "franka_panda",
        target_fps: int = 10,
        enable_smoothing: bool = True,
        enable_safety: bool = True,
    ):
        """Connect to streaming server.

        Args:
            model: VLA model to use
            robot_type: Robot type
            target_fps: Target inference rate (Hz)
            enable_smoothing: Enable action smoothing
            enable_safety: Enable safety monitoring
        """
        print(f"Connecting to {self.api_url}...")

        # Connect WebSocket
        self.websocket = await websockets.connect(self.api_url)

        # Authenticate
        auth_message = {
            "type": "auth",
            "api_key": self.api_key,
            "model": model,
            "robot_type": robot_type,
            "target_fps": target_fps,
            "enable_smoothing": enable_smoothing,
            "enable_safety": enable_safety,
        }

        await self.websocket.send(json.dumps(auth_message))

        # Wait for confirmation
        response = await self.websocket.recv()
        data = json.loads(response)

        if data["type"] == "connected":
            self.session_id = data["session_id"]
            self.is_connected = True
            print(f"✅ Connected! Session ID: {self.session_id}")
            print(f"   Model: {data['config']['model']}")
            print(f"   Target FPS: {data['config']['target_fps']}")
            print(f"   Smoothing: {data['config']['smoothing']}")
            print(f"   Safety: {data['config']['safety']}")
        else:
            raise RuntimeError(f"Connection failed: {data.get('message')}")

    async def send_frame(
        self,
        image: np.ndarray,
        instruction: str,
        robot_state: dict = None,
    ):
        """Send a frame for inference.

        Args:
            image: Image as numpy array (BGR format from OpenCV)
            instruction: Natural language instruction
            robot_state: Optional robot state dictionary
        """
        if not self.is_connected:
            raise RuntimeError("Not connected")

        # Convert image to base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')

        # Create message
        message = {
            "type": "frame",
            "image": f"data:image/jpeg;base64,{image_base64}",
            "instruction": instruction,
        }

        if robot_state:
            message["robot_state"] = robot_state

        # Send
        await self.websocket.send(json.dumps(message))

    async def receive_action(self, timeout: float = 1.0):
        """Receive next action from server.

        Args:
            timeout: Timeout in seconds

        Returns:
            Action dictionary or None
        """
        if not self.is_connected:
            raise RuntimeError("Not connected")

        try:
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout
            )

            data = json.loads(response)

            if data["type"] == "action":
                return data
            elif data["type"] == "error":
                print(f"❌ Error: {data['message']}")
                return None
            elif data["type"] == "warning":
                print(f"⚠️  Warning: {data['message']}")
                return None

        except asyncio.TimeoutError:
            return None

    async def get_stats(self):
        """Request session statistics."""
        if not self.is_connected:
            raise RuntimeError("Not connected")

        await self.websocket.send(json.dumps({"type": "stats"}))

        response = await self.websocket.recv()
        data = json.loads(response)

        if data["type"] == "stats":
            return data

    async def close(self):
        """Close connection."""
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "close"}))
            await self.websocket.close()
            self.is_connected = False
            print("Connection closed")


async def example_webcam_streaming():
    """Example: Stream from webcam for real-time inference."""

    # Configuration
    API_URL = "ws://localhost:8000/v1/stream"
    API_KEY = "vla_live_your_key_here"  # Replace with your API key

    # Create client
    client = VLAStreamingClient(API_URL, API_KEY)

    try:
        # Connect
        await client.connect(
            model="openvla-7b",
            target_fps=10,
            enable_smoothing=True,
            enable_safety=True,
        )

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Failed to open webcam")
            return

        print("\n🎥 Streaming from webcam (press 'q' to quit)...")
        print("   Sending frames and receiving actions in real-time\n")

        frame_count = 0
        start_time = time.time()

        while True:
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                break

            # Send frame
            await client.send_frame(
                image=frame,
                instruction="pick up the red object",
            )

            # Receive action (non-blocking)
            action_data = await client.receive_action(timeout=0.1)

            if action_data:
                action = action_data["action"]
                safety_score = action_data["safety_score"]
                latency_ms = action_data["latency_ms"]

                # Display on frame
                text = f"Action: [{action[0]:.2f}, {action[1]:.2f}, {action[2]:.2f}, ...]"
                cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                text2 = f"Safety: {safety_score:.2f} | Latency: {latency_ms}ms"
                cv2.putText(frame, text2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Print to console
                print(f"Frame {frame_count}: Action={action[:3]}, Safety={safety_score:.2f}, Latency={latency_ms}ms")

            frame_count += 1

            # Display frame
            cv2.imshow("VLA Streaming Inference", frame)

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Print stats every 100 frames
            if frame_count % 100 == 0:
                stats = await client.get_stats()
                elapsed = time.time() - start_time
                actual_fps = frame_count / elapsed
                print(f"\n📊 Stats after {frame_count} frames:")
                print(f"   Actual FPS: {actual_fps:.1f}")
                print(f"   Dropped frames: {stats.get('dropped_frames', 0)}")
                print(f"   Avg latency: {stats.get('avg_latency_ms', 0):.1f}ms\n")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Cleanup
        await client.close()
        cap.release()
        cv2.destroyAllWindows()


async def example_video_file_streaming():
    """Example: Stream from video file."""

    API_URL = "ws://localhost:8000/v1/stream"
    API_KEY = "vla_live_your_key_here"  # Replace with your API key

    # Create client
    client = VLAStreamingClient(API_URL, API_KEY)

    try:
        await client.connect(target_fps=30)

        # Open video file
        video_path = "robot_demo.mp4"  # Replace with your video
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"❌ Failed to open video: {video_path}")
            return

        print(f"🎬 Processing video: {video_path}")

        frame_count = 0
        actions = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Send frame
            await client.send_frame(
                image=frame,
                instruction="navigate to the target location",
            )

            # Receive action
            action_data = await client.receive_action(timeout=1.0)

            if action_data:
                actions.append(action_data["action"])
                print(f"Frame {frame_count}: Received action")

            frame_count += 1

        print(f"\n✅ Processed {frame_count} frames")
        print(f"   Generated {len(actions)} actions")

        # Save actions
        np.save("actions.npy", np.array(actions))
        print(f"   Actions saved to actions.npy")

    finally:
        await client.close()
        cap.release()


async def example_simulated_robot_control():
    """Example: Simulated robot control loop."""

    API_URL = "ws://localhost:8000/v1/stream"
    API_KEY = "vla_live_your_key_here"

    client = VLAStreamingClient(API_URL, API_KEY)

    try:
        await client.connect(
            target_fps=20,
            enable_smoothing=True,
            enable_safety=True,
        )

        # Simulate robot control loop
        print("🤖 Simulated robot control loop (10 seconds)...")

        # Simulated robot state
        robot_pose = [0.3, 0.0, 0.5, 0.0, 0.0, 0.0]  # [x, y, z, roll, pitch, yaw]

        start_time = time.time()
        control_loop_count = 0

        while time.time() - start_time < 10.0:
            loop_start = time.time()

            # Simulate camera capture (load from file or generate)
            # In real robot, this would be: frame = robot.get_camera_frame()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Placeholder

            # Send frame with robot state
            await client.send_frame(
                image=frame,
                instruction="reach the target position",
                robot_state={
                    "pose": robot_pose,
                    "velocity": [0.0] * 6,
                }
            )

            # Receive action
            action_data = await client.receive_action(timeout=0.1)

            if action_data:
                action = action_data["action"]
                safety_score = action_data["safety_score"]

                # Apply action to robot (simulated)
                # In real robot: robot.execute_action(action)
                robot_pose[0] += action[0]  # Update x position
                robot_pose[1] += action[1]  # Update y position
                robot_pose[2] += action[2]  # Update z position

                print(f"Control loop {control_loop_count}: "
                      f"Pose=[{robot_pose[0]:.2f}, {robot_pose[1]:.2f}, {robot_pose[2]:.2f}], "
                      f"Safety={safety_score:.2f}")

            control_loop_count += 1

            # Maintain control frequency (50Hz = 20ms per loop)
            elapsed = time.time() - loop_start
            if elapsed < 0.02:
                await asyncio.sleep(0.02 - elapsed)

        print(f"\n✅ Completed {control_loop_count} control loops")

    finally:
        await client.close()


if __name__ == "__main__":
    print("VLA Streaming Client Examples")
    print("=" * 50)
    print("\nChoose example:")
    print("1. Webcam streaming")
    print("2. Video file streaming")
    print("3. Simulated robot control")
    print()

    choice = input("Enter choice (1-3): ")

    if choice == "1":
        asyncio.run(example_webcam_streaming())
    elif choice == "2":
        asyncio.run(example_video_file_streaming())
    elif choice == "3":
        asyncio.run(example_simulated_robot_control())
    else:
        print("Invalid choice")
