"""WebSocket streaming API router for real-time robot control."""

import asyncio
import base64
import io
import json
import logging
from typing import Dict

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from PIL import Image

from src.api.dependencies import get_db
from src.middleware.authentication import APIKeyInfo, verify_api_key
from src.services.streaming_inference import streaming_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["streaming"])


@router.websocket("/stream")
async def stream_inference(websocket: WebSocket):
    """WebSocket endpoint for live streaming inference.

    Protocol:
        Client -> Server (messages):
            {
                "type": "auth",
                "api_key": "vla_live_...",
                "model": "openvla-7b",
                "robot_type": "franka_panda",
                "target_fps": 10,
                "enable_smoothing": true,
                "enable_safety": true
            }

            {
                "type": "frame",
                "frame_id": 123,
                "image": "<base64_encoded_image>",
                "instruction": "pick up the red cube",
                "robot_state": {
                    "pose": [x, y, z, roll, pitch, yaw],
                    "velocity": [...]
                }
            }

            {
                "type": "close"
            }

        Server -> Client (messages):
            {
                "type": "connected",
                "session_id": "uuid",
                "status": "ready"
            }

            {
                "type": "action",
                "frame_id": 123,
                "action": [0.05, -0.02, 0.10, 0.0, 0.0, 0.1, 1.0],
                "safety_score": 0.95,
                "latency_ms": 45,
                "smoothed": true
            }

            {
                "type": "stats",
                "total_frames": 1234,
                "dropped_frames": 5,
                "actual_fps": 9.8,
                "avg_latency_ms": 42.3
            }

            {
                "type": "error",
                "message": "..."
            }
    """
    await websocket.accept()
    logger.info(f"WebSocket connection from {websocket.client}")

    session = None
    api_key_info = None

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "auth":
                # Authentication
                try:
                    # Validate API key
                    from src.core.security import hash_api_key
                    from src.middleware.authentication import verify_api_key
                    from sqlalchemy import select
                    from sqlalchemy.ext.asyncio import AsyncSession
                    from src.core.database import db_manager
                    from src.models.database import APIKey, Customer

                    api_key = message.get("api_key")
                    if not api_key:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing API key"
                        })
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                        return

                    # Validate key (simplified - should use proper auth)
                    key_hash = hash_api_key(api_key)

                    async with db_manager.get_session() as db_session:
                        result = await db_session.execute(
                            select(APIKey, Customer)
                            .join(Customer, APIKey.customer_id == Customer.customer_id)
                            .where(APIKey.key_hash == key_hash)
                            .where(APIKey.is_active == True)
                            .where(Customer.is_active == True)
                        )
                        row = result.first()

                        if not row:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Invalid API key"
                            })
                            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                            return

                        api_key_obj = row[0]
                        customer = row[1]

                    # Create streaming session
                    session = await streaming_manager.create_session(
                        customer_id=customer.customer_id,
                        model_id=message.get("model", "openvla-7b"),
                        robot_type=message.get("robot_type", "franka_panda"),
                        target_fps=message.get("target_fps", 10),
                        enable_smoothing=message.get("enable_smoothing", True),
                        enable_safety=message.get("enable_safety", True),
                    )

                    # Send confirmation
                    await websocket.send_json({
                        "type": "connected",
                        "session_id": str(session.session_id),
                        "status": "ready",
                        "config": {
                            "model": session.model_id,
                            "target_fps": session.target_fps,
                            "smoothing": session.enable_smoothing,
                            "safety": session.enable_safety,
                        }
                    })

                    # Start action sender task
                    asyncio.create_task(send_actions(websocket, session))

                except Exception as e:
                    logger.error(f"Auth error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Authentication failed: {e}"
                    })
                    await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                    return

            elif msg_type == "frame":
                # Process frame
                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not authenticated"
                    })
                    continue

                try:
                    # Decode image
                    image_data = message.get("image")
                    if not image_data:
                        continue

                    # Handle base64
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]

                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))

                    # Submit frame
                    frame_id = await session.submit_frame(
                        image=image,
                        instruction=message.get("instruction"),
                        robot_state=message.get("robot_state"),
                    )

                except asyncio.QueueFull:
                    await websocket.send_json({
                        "type": "warning",
                        "message": "Frame dropped - queue full"
                    })
                except Exception as e:
                    logger.error(f"Frame processing error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Frame processing failed: {e}"
                    })

            elif msg_type == "stats":
                # Send statistics
                if session:
                    stats = session.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        **stats
                    })

            elif msg_type == "close":
                # Close session
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cleanup
        if session:
            await streaming_manager.close_session(session.session_id)


async def send_actions(websocket: WebSocket, session):
    """Background task to send actions to client.

    Args:
        websocket: WebSocket connection
        session: StreamingInferenceSession
    """
    try:
        while session.is_running:
            # Get next action
            action = await session.get_action(timeout=0.1)

            if action:
                # Send to client
                await websocket.send_json({
                    "type": "action",
                    "frame_id": action.frame_id,
                    "timestamp": action.timestamp,
                    "action": action.action,
                    "safety_score": action.safety_score,
                    "latency_ms": action.latency_ms,
                    "smoothed": action.smoothed,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Action sender error: {e}", exc_info=True)


@router.get("/stream/sessions")
async def list_streaming_sessions():
    """List active streaming sessions (admin endpoint).

    Returns:
        List of active session statistics
    """
    sessions_info = []

    for session_id, session in streaming_manager.sessions.items():
        sessions_info.append(session.get_stats())

    return {
        "active_sessions": len(sessions_info),
        "sessions": sessions_info
    }
