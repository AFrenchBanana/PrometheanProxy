#!/usr/bin/env python3
"""
Beacon WebSocket Server

Provides a lightweight WebSocket server to broadcast:
- Live events (connection stats, check-ins)
- Beacon-specific updates
- Command/task lifecycle updates

This is designed to complement the existing beacon HTTP server and mirror
the "live events" functionality of the MultiHandler by enabling a web UI
to subscribe and receive real-time updates.

WebSocket Paths:
- /ws/events               -> Global events stream
- /ws/beacons/<uuid>       -> Beacon-specific updates
- /ws/commands             -> Global command/task updates

Usage:
    from Modules.beacon.beacon_server.websocket_server import (
        start_websocket_server,
        publish_event,
        publish_beacon_update,
        publish_command_update,
    )

    start_websocket_server(config)  # non-blocking

    publish_event({"sessions": 5, "beacons": 12})
    publish_beacon_update("abc-uuid", {"status": "checked_in"})
    publish_command_update({"uuid": "cmd-123", "state": "sent", "target": "host-1"})

Notes:
- If websockets package is unavailable at runtime, the server will be disabled
  but publish_* calls will still succeed (no-op) and log a warning once.
"""

import asyncio
import json
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

try:
    import websockets  # type: ignore
    from websockets.server import WebSocketServerProtocol as _WSProto  # type: ignore

    _WS_AVAILABLE = True
except Exception:
    websockets = None
    _WSProto = None
    _WS_AVAILABLE = False

from Modules.global_objects import logger

# ============================================================================
# Topic Registry and Broadcast Manager
# ============================================================================


@dataclass
class Topic:
    """Represents a WebSocket broadcast topic."""

    name: str
    subscribers: Set[Any] = field(default_factory=set)


class BroadcastManager:
    """
    Manages WebSocket topics and broadcasting messages to subscribers.

    Topics:
      - events: global live events
      - commands: command/task lifecycle feed
      - beacons/<uuid>: beacon-specific channel
    """

    def __init__(self):
        self._topics: Dict[str, Topic] = {}
        self._warned_no_ws: bool = False

    def _ensure_topic(self, name: str) -> Topic:
        if name not in self._topics:
            self._topics[name] = Topic(name=name)
        return self._topics[name]

    def subscribe(self, topic_name: str, ws: Any) -> None:
        topic = self._ensure_topic(topic_name)
        topic.subscribers.add(ws)
        logger.debug(f"WebSocket subscribed to topic '{topic_name}'")

    def unsubscribe(self, topic_name: str, ws: Any) -> None:
        topic = self._topics.get(topic_name)
        if topic and ws in topic.subscribers:
            topic.subscribers.remove(ws)
            logger.debug(f"WebSocket unsubscribed from topic '{topic_name}'")

    def broadcast(self, topic_name: str, payload: dict) -> None:
        """
        Broadcast a JSON payload to all subscribers of a topic.
        Safe to call from non-async contexts.
        """
        if websockets is None:
            # Warn only once to avoid log spam
            if not self._warned_no_ws:
                logger.warning(
                    "WebSocket server not available (missing 'websockets' package). "
                    "Live events will be disabled."
                )
                self._warned_no_ws = True
            return

        topic = self._topics.get(topic_name)
        if not topic or not topic.subscribers:
            return

        try:
            message = json.dumps(payload)
        except Exception as e:
            logger.error(f"Failed to serialize broadcast payload: {e}")
            return

        # Schedule async send on the running loop
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._async_broadcast(topic, message))
        )

    async def _async_broadcast(self, topic: Topic, message: str) -> None:
        dead: Set[Any] = set()
        for ws in list(topic.subscribers):
            try:
                await ws.send(message)
            except Exception:
                dead.add(ws)
        # Clean up dead subscribers
        for ws in dead:
            if ws in topic.subscribers:
                topic.subscribers.remove(ws)
        if dead:
            logger.debug(
                f"Cleaned {len(dead)} dead subscribers from topic '{topic.name}'"
            )


_broadcast_manager = BroadcastManager()


# ============================================================================
# Public publish helpers (UI/handlers can call these)
# ============================================================================


def publish_event(event: dict) -> None:
    """
    Publish a global live event (e.g., connection stats).

    Example payload:
        {
            "type": "connection_stats",
            "sessions": 4,
            "beacons": 12,
            "ts": 1700000000.123
        }
    """
    _broadcast_manager.broadcast("events", event)


def publish_beacon_update(beacon_uuid: str, update: dict) -> None:
    """
    Publish a beacon-specific update.

    Example payload:
        {
            "type": "beacon_checkin",
            "uuid": "<beacon_uuid>",
            "hostname": "host-01",
            "next_beacon": 1700001000.0
        }
    """
    _broadcast_manager.broadcast(f"beacons/{beacon_uuid}", update)


def publish_command_update(update: dict) -> None:
    """
    Publish a command/task lifecycle update.

    Example payload:
        {
            "type": "command",
            "uuid": "cmd-abc",
            "state": "sent|received|completed|error",
            "target": "host-01",
            "output": "..."
        }
    """
    _broadcast_manager.broadcast("commands", update)


# ============================================================================
# WebSocket Server Implementation
# ============================================================================

_PATH_RE = re.compile(
    r"^/ws/(?P<section>events|commands|beacons)(?:/(?P<uuid>[^/]+))?$"
)


async def _ws_handler(ws: Any, path: str):
    """
    Handle a websocket connection:
      - Parse path and subscribe to the correct topic
      - Optionally echo/handle incoming control messages (JSON)
      - Unsubscribe on disconnect
    """
    match = _PATH_RE.match(path)
    if not match:
        await ws.close(code=4000, reason="Invalid path")
        return

    gd = match.groupdict()
    section = gd.get("section")
    beacon_uuid = gd.get("uuid")

    if section == "beacons":
        if not beacon_uuid:
            await ws.close(code=4001, reason="Missing beacon UUID")
            return
        topic_name = f"beacons/{beacon_uuid}"
    else:
        topic_name = section  # 'events' or 'commands'

    _broadcast_manager.subscribe(topic_name, ws)

    # Acknowledge subscription
    try:
        await ws.send(json.dumps({"subscribed": topic_name}))
    except Exception:
        pass

    # Optional: handle client messages (e.g., ping, filters)
    try:
        async for message in ws:
            # Expect JSON control messages
            try:
                data = json.loads(message)
            except Exception:
                # Non-JSON messages are ignored
                continue

            # Minimal protocol:
            # { "type": "ping" } -> reply { "type": "pong" }
            # { "type": "echo", "payload": {...} } -> reply with same payload
            msg_type = data.get("type")
            if msg_type == "ping":
                await ws.send(json.dumps({"type": "pong"}))
            elif msg_type == "echo":
                await ws.send(
                    json.dumps({"type": "echo", "payload": data.get("payload")})
                )
            # Future: add filters, auth, etc.
    except Exception:
        # Connection closed or error
        pass
    finally:
        _broadcast_manager.unsubscribe(topic_name, ws)


def _run_ws_server(host: str, port: int):
    """
    Run the WebSocket server on an asyncio loop.
    """
    if websockets is None:
        logger.warning(
            "Cannot start WebSocket server: 'websockets' package not available."
        )
        return

    async def _main():
        logger.info(f"Starting Beacon WebSocket server on ws://{host}:{port}")
        try:
            async with websockets.serve(_ws_handler, host, port):
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.critical(f"Beacon WebSocket server failed: {e}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_main())


# ============================================================================
# Public API
# ============================================================================


def start_websocket_server(config: Dict) -> Optional[threading.Thread]:
    """
    Start the WebSocket server in a background thread.

    Config expects:
      config["server"]["listenaddress"]
      config["server"]["websocketPort"] (new; add to your config)
        - If not provided, falls back to config["server"]["webPort"] + 1

    Returns:
      Thread object if the server started, or None if websockets missing.
    """
    host = config["server"]["listenaddress"]
    port = config["server"].get("websocketPort") or int(config["server"]["webPort"]) + 1

    if websockets is None:
        logger.warning(
            "WebSocket server is disabled (missing 'websockets'). "
            "Install it to enable live events over WebSockets."
        )
        return None

    thread = threading.Thread(target=_run_ws_server, args=(host, port), daemon=True)
    thread.start()
    return thread


# Convenience hooks to mirror MultiHandler-style logging to WebSocket topics


def log_live_connection_stats(sessions_count: int, beacons_count: int) -> None:
    """
    Convenience method to publish connection stats to the events topic.
    """
    publish_event(
        {
            "type": "connection_stats",
            "sessions": sessions_count,
            "beacons": beacons_count,
        }
    )


def log_beacon_checkin(
    uuid: str, hostname: Optional[str] = None, next_beacon_ts: Optional[float] = None
) -> None:
    """
    Publish a beacon check-in event on both the global and the per-beacon topic.
    """
    payload = {
        "type": "beacon_checkin",
        "uuid": uuid,
    }
    if hostname is not None:
        payload["hostname"] = hostname
    if next_beacon_ts is not None:
        payload["next_beacon_ts"] = next_beacon_ts

    publish_event(payload)
    publish_beacon_update(uuid, payload)


def log_command_lifecycle(
    command_uuid: str,
    state: str,
    command_name: Optional[str] = None,
    target_hostname: Optional[str] = None,
    output: Optional[str] = None,
) -> None:
    """
    Publish command lifecycle updates to the commands topic.
    States can include: sent, received, executing, completed, error.
    """
    payload = {
        "type": "command",
        "uuid": command_uuid,
        "state": state,
    }
    if command_name is not None:
        payload["command"] = command_name
    if target_hostname is not None:
        payload["target"] = target_hostname
    if output is not None:
        payload["output"] = output

    publish_command_update(payload)
