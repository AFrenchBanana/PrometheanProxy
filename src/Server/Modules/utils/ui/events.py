"""
UI Events Module - Event Management for Terminal Display

Provides the Event class for tracking and displaying activity events
in the PrometheanProxy terminal interface.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .theme import EVENT_STYLES


class Event:
    """
    Represents a single event in the activity feed.

    Events are displayed in the terminal to show real-time activity
    such as new connections, commands, check-ins, etc.

    Attributes:
        timestamp: Formatted time string when event occurred
        event_type: Category of event (session, beacon, command, etc.)
        message: Human-readable event description
        details: Additional metadata about the event
        icon: Display icon for the event type
        color: Rich color string for styling
        prefix: Label prefix for the event type
    """

    def __init__(
        self,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize a new Event.

        Args:
            event_type: Category of event (e.g., "session", "beacon", "command")
            message: Human-readable description of the event
            details: Optional dictionary with additional event metadata
        """
        self.timestamp = datetime.now().strftime("%H:%M:%S")
        self.event_type = event_type
        self.message = message
        self.details = details or {}

        # Get styling from theme, with fallback for unknown types
        style = EVENT_STYLES.get(event_type, ("•", "white", "EVENT"))
        self.icon = style[0]
        self.color = style[1]
        self.prefix = style[2]

    def __str__(self) -> str:
        """Return formatted string representation of the event."""
        return f"[{self.timestamp}] {self.prefix}: {self.message}"

    def __repr__(self) -> str:
        """Return debug representation of the event."""
        return (
            f"Event(type={self.event_type!r}, message={self.message!r}, "
            f"timestamp={self.timestamp!r})"
        )

    def to_rich(self) -> str:
        """
        Format event for Rich console output.

        Returns:
            String with Rich markup for styled terminal display
        """
        return (
            f"[dim]{self.timestamp}[/] "
            f"[{self.color}]{self.icon}[/] "
            f"[bold {self.color}]{self.prefix}[/] "
            f"{self.message}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary format.

        Returns:
            Dictionary containing all event data
        """
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "message": self.message,
            "details": self.details,
            "icon": self.icon,
            "color": self.color,
            "prefix": self.prefix,
        }


class EventFactory:
    """Factory class for creating common event types."""

    @staticmethod
    def session_connect(hostname: str, ip: str, os: str) -> Event:
        """Create a new session connection event."""
        return Event(
            "session_new",
            f"[bright_green]{hostname}[/] ({ip}) - {os}",
            {"hostname": hostname, "ip": ip, "os": os},
        )

    @staticmethod
    def session_disconnect(hostname: str, ip: str) -> Event:
        """Create a session disconnection event."""
        return Event(
            "disconnect",
            f"[dim]{hostname}[/] ({ip}) disconnected",
            {"hostname": hostname, "ip": ip, "type": "session"},
        )

    @staticmethod
    def beacon_connect(hostname: str, ip: str, os: str, uuid: str) -> Event:
        """Create a new beacon connection event."""
        uuid_short = uuid[:8] if len(uuid) > 8 else uuid
        return Event(
            "beacon_new",
            f"[bright_cyan]{hostname}[/] ({ip}) [{uuid_short}...]",
            {"hostname": hostname, "ip": ip, "os": os, "uuid": uuid},
        )

    @staticmethod
    def beacon_checkin(hostname: str, ip: str, uuid: str) -> Event:
        """Create a beacon check-in event."""
        uuid_short = uuid[:8] if len(uuid) > 8 else uuid
        return Event(
            "beacon_checkin",
            f"[cyan]{hostname}[/] ({ip}) [{uuid_short}...]",
            {"hostname": hostname, "ip": ip, "uuid": uuid},
        )

    @staticmethod
    def beacon_disconnect(hostname: str, ip: str) -> Event:
        """Create a beacon disconnection event."""
        return Event(
            "disconnect",
            f"[dim]{hostname}[/] ({ip}) disconnected",
            {"hostname": hostname, "ip": ip, "type": "beacon"},
        )

    @staticmethod
    def command_sent(command: str, target: str) -> Event:
        """Create a command sent event."""
        cmd_preview = command[:30] + "..." if len(command) > 30 else command
        return Event(
            "command_sent",
            f"[yellow]{cmd_preview}[/] → {target}",
            {"command": command, "target": target},
        )

    @staticmethod
    def command_output(command: str, target: str) -> Event:
        """Create a command output received event."""
        cmd_preview = command[:30] + "..." if len(command) > 30 else command
        return Event(
            "command_output",
            f"[bright_blue]{cmd_preview}[/] ← {target}",
            {"command": command, "target": target},
        )

    @staticmethod
    def command_error(command: str, target: str, error: str = "") -> Event:
        """Create a command error event."""
        cmd_preview = command[:20] + "..." if len(command) > 20 else command
        msg = f"[bright_red]{cmd_preview}[/] on {target}"
        if error:
            msg += f": {error[:30]}"
        return Event(
            "command_error",
            msg,
            {"command": command, "target": target, "error": error},
        )

    @staticmethod
    def module_loaded(module_name: str, target: str) -> Event:
        """Create a module loaded event."""
        return Event(
            "module",
            f"[bright_magenta]{module_name}[/] loaded on {target}",
            {"module": module_name, "target": target},
        )

    @staticmethod
    def info(message: str) -> Event:
        """Create an info event."""
        return Event("info", message)

    @staticmethod
    def warning(message: str) -> Event:
        """Create a warning event."""
        return Event("warning", f"[yellow]{message}[/]")

    @staticmethod
    def error(message: str) -> Event:
        """Create an error event."""
        return Event("error", f"[bright_red]{message}[/]")

    @staticmethod
    def success(message: str) -> Event:
        """Create a success event."""
        return Event("success", f"[bright_green]{message}[/]")
