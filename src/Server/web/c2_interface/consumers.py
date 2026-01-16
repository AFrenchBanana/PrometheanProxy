"""
WebSocket Consumers for PrometheanProxy C2 Interface

This module provides WebSocket consumers for real-time event streaming,
including beacon updates, command execution results, and live system events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseConsumer(AsyncWebsocketConsumer):
    """
    Base WebSocket consumer with common functionality.

    Provides connection management, message handling, and error handling
    for all WebSocket consumers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Handle WebSocket connection."""
        # Accept the connection
        await self.accept()

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        logger.info(f"WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Cancel heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        # Leave room group if joined
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        logger.info(f"WebSocket disconnected: {self.channel_name} (code: {close_code})")

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming WebSocket messages.

        Expected message format:
        {
            "type": "message_type",
            "data": {...}
        }
        """
        try:
            if text_data:
                message = json.loads(text_data)
                message_type = message.get("type")

                # Handle different message types
                if message_type == "ping":
                    await self.send_message("pong", {"timestamp": self.get_timestamp()})
                elif message_type == "subscribe":
                    await self.handle_subscribe(message.get("data", {}))
                elif message_type == "unsubscribe":
                    await self.handle_unsubscribe(message.get("data", {}))
                else:
                    await self.handle_message(message_type, message.get("data", {}))

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")

    async def handle_message(self, message_type: str, data: Dict[str, Any]):
        """
        Handle custom message types.
        Override in subclasses for specific message handling.
        """
        logger.warning(f"Unhandled message type: {message_type}")

    async def handle_subscribe(self, data: Dict[str, Any]):
        """Handle subscription requests. Override in subclasses."""
        pass

    async def handle_unsubscribe(self, data: Dict[str, Any]):
        """Handle unsubscription requests. Override in subclasses."""
        pass

    async def send_message(self, message_type: str, data: Any = None):
        """
        Send a message to the WebSocket client.

        Args:
            message_type: Type of message
            data: Message data
        """
        message = {
            "type": message_type,
            "data": data,
            "timestamp": self.get_timestamp(),
        }
        await self.send(text_data=json.dumps(message))

    async def send_error(self, error: str, detail: Optional[str] = None):
        """Send an error message to the client."""
        await self.send_message(
            "error",
            {"error": error, "detail": detail} if detail else {"error": error},
        )

    async def heartbeat_loop(self):
        """Send periodic heartbeat messages to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
                await self.send_message(
                    "heartbeat", {"timestamp": self.get_timestamp()}
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + "Z"


class EventsConsumer(BaseConsumer):
    """
    WebSocket consumer for global C2 events.

    Streams all system events including:
    - New beacon connections
    - Beacon check-ins
    - Session updates
    - Command executions
    - System alerts
    """

    async def connect(self):
        """Handle connection and join events group."""
        # Join the global events group
        self.room_group_name = "c2_events"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await super().connect()

        # Send welcome message
        await self.send_message(
            "connected",
            {
                "message": "Connected to C2 event stream",
                "room": self.room_group_name,
            },
        )

    # Channel layer message handlers
    async def beacon_event(self, event):
        """Handle beacon events from channel layer."""
        await self.send_message("beacon_event", event.get("data"))

    async def session_event(self, event):
        """Handle session events from channel layer."""
        await self.send_message("session_event", event.get("data"))

    async def command_event(self, event):
        """Handle command events from channel layer."""
        await self.send_message("command_event", event.get("data"))

    async def system_event(self, event):
        """Handle system events from channel layer."""
        await self.send_message("system_event", event.get("data"))


class BeaconConsumer(BaseConsumer):
    """
    WebSocket consumer for specific beacon monitoring.

    Provides real-time updates for a specific beacon including:
    - Check-in events
    - Command results
    - Status changes
    - Connection metrics
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beacon_uuid: Optional[str] = None

    async def connect(self):
        """Handle connection and join beacon-specific group."""
        # Get beacon UUID from URL
        self.beacon_uuid = self.scope["url_route"]["kwargs"].get("uuid")

        if not self.beacon_uuid:
            await self.close(code=4000)
            return

        # Join beacon-specific group
        self.room_group_name = f"beacon_{self.beacon_uuid}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await super().connect()

        # Send welcome message
        await self.send_message(
            "connected",
            {
                "message": f"Connected to beacon {self.beacon_uuid}",
                "uuid": self.beacon_uuid,
            },
        )

    # Channel layer message handlers
    async def beacon_checkin(self, event):
        """Handle beacon check-in events."""
        await self.send_message("checkin", event.get("data"))

    async def beacon_command_result(self, event):
        """Handle command result events."""
        await self.send_message("command_result", event.get("data"))

    async def beacon_status(self, event):
        """Handle beacon status change events."""
        await self.send_message("status_change", event.get("data"))

    async def beacon_disconnected(self, event):
        """Handle beacon disconnection events."""
        await self.send_message("disconnected", event.get("data"))


class SessionConsumer(BaseConsumer):
    """
    WebSocket consumer for interactive session monitoring.

    Provides real-time updates for interactive sessions including:
    - Session I/O
    - Command execution
    - File transfers
    - Session status
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_uuid: Optional[str] = None

    async def connect(self):
        """Handle connection and join session-specific group."""
        # Get session UUID from URL
        self.session_uuid = self.scope["url_route"]["kwargs"].get("uuid")

        if not self.session_uuid:
            await self.close(code=4000)
            return

        # Join session-specific group
        self.room_group_name = f"session_{self.session_uuid}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await super().connect()

        # Send welcome message
        await self.send_message(
            "connected",
            {
                "message": f"Connected to session {self.session_uuid}",
                "uuid": self.session_uuid,
            },
        )

    async def handle_message(self, message_type: str, data: Dict[str, Any]):
        """Handle session-specific messages."""
        if message_type == "input":
            # Handle user input for the session
            await self.handle_session_input(data)
        else:
            await super().handle_message(message_type, data)

    async def handle_session_input(self, data: Dict[str, Any]):
        """Handle input sent to the session."""
        # This would integrate with the session handler
        # For now, just acknowledge receipt
        await self.send_message("input_received", {"status": "acknowledged"})

    # Channel layer message handlers
    async def session_output(self, event):
        """Handle session output events."""
        await self.send_message("output", event.get("data"))

    async def session_command_result(self, event):
        """Handle command result events."""
        await self.send_message("command_result", event.get("data"))

    async def session_status(self, event):
        """Handle session status change events."""
        await self.send_message("status_change", event.get("data"))

    async def session_closed(self, event):
        """Handle session closed events."""
        await self.send_message("closed", event.get("data"))


class ConnectionsConsumer(BaseConsumer):
    """
    WebSocket consumer for monitoring all connections.

    Provides real-time updates about all beacons and sessions:
    - Connection list updates
    - New connections
    - Disconnections
    - Status changes
    """

    async def connect(self):
        """Handle connection and join connections monitoring group."""
        # Join the connections monitoring group
        self.room_group_name = "all_connections"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await super().connect()

        # Send welcome message
        await self.send_message(
            "connected",
            {
                "message": "Connected to connections monitor",
                "room": self.room_group_name,
            },
        )

    # Channel layer message handlers
    async def connection_added(self, event):
        """Handle new connection events."""
        await self.send_message("connection_added", event.get("data"))

    async def connection_removed(self, event):
        """Handle connection removed events."""
        await self.send_message("connection_removed", event.get("data"))

    async def connection_updated(self, event):
        """Handle connection update events."""
        await self.send_message("connection_updated", event.get("data"))

    async def connections_list(self, event):
        """Handle full connections list events."""
        await self.send_message("connections_list", event.get("data"))


class CommandConsumer(BaseConsumer):
    """
    WebSocket consumer for command monitoring and execution.

    Provides real-time updates about command execution:
    - Command queue updates
    - Execution status
    - Results streaming
    - Error notifications
    """

    async def connect(self):
        """Handle connection and join command monitoring group."""
        # Join the command monitoring group
        self.room_group_name = "command_monitor"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await super().connect()

        # Send welcome message
        await self.send_message(
            "connected",
            {
                "message": "Connected to command monitor",
                "room": self.room_group_name,
            },
        )

    async def handle_message(self, message_type: str, data: Dict[str, Any]):
        """Handle command-specific messages."""
        if message_type == "execute":
            # Handle command execution request
            await self.handle_execute_command(data)
        else:
            await super().handle_message(message_type, data)

    async def handle_execute_command(self, data: Dict[str, Any]):
        """Handle command execution request from WebSocket."""
        uuid = data.get("uuid")
        command = data.get("command")

        if not uuid or not command:
            await self.send_error("Missing uuid or command")
            return

        # Send acknowledgment
        await self.send_message(
            "command_queued",
            {
                "uuid": uuid,
                "command": command,
                "status": "queued",
            },
        )

    # Channel layer message handlers
    async def command_queued(self, event):
        """Handle command queued events."""
        await self.send_message("command_queued", event.get("data"))

    async def command_executing(self, event):
        """Handle command executing events."""
        await self.send_message("command_executing", event.get("data"))

    async def command_completed(self, event):
        """Handle command completed events."""
        await self.send_message("command_completed", event.get("data"))

    async def command_failed(self, event):
        """Handle command failed events."""
        await self.send_message("command_failed", event.get("data"))

    async def command_output(self, event):
        """Handle command output streaming events."""
        await self.send_message("command_output", event.get("data"))
