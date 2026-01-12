"""
UI Manager Module - Core Terminal Interface Manager

Provides the UIManager singleton class for managing terminal output
with modern styling and live event updates.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from rich.console import Console

from .events import Event, EventFactory
from .tables import (
    create_beacons_table,
    create_command_history_table,
    create_help_table,
    create_sessions_table,
    create_status_table,
    create_users_table,
)
from .theme import PROMETHEAN_THEME


class UIManager:
    """
    Manages terminal output with modern styling and live event updates.

    This is a singleton class that provides a clean single-terminal experience
    with thread-safe output, event tracking, and statistics management.

    Attributes:
        console: Rich Console instance for styled output
        events: Deque of recent events for display
        stats: Dictionary of connection statistics
    """

    _instance: Optional["UIManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "UIManager":
        """Singleton pattern to ensure only one UI manager exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_events: int = 100) -> None:
        """
        Initialize the UI Manager.

        Args:
            max_events: Maximum number of events to keep in history
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True
        self.console: Console = Console(theme=PROMETHEAN_THEME, highlight=False)
        self.events: Deque[Event] = deque(maxlen=max_events)

        self.stats: Dict[str, Any] = {
            "sessions": 0,
            "beacons": 0,
            "total_connections": 0,
            "commands_executed": 0,
            "last_activity": "None",
            "server_uptime": datetime.now(),
        }

        self._print_lock = threading.Lock()

    # =========================================================================
    # Console Output Methods
    # =========================================================================

    def print(self, *args, **kwargs) -> None:
        """Thread-safe print to console."""
        with self._print_lock:
            self.console.print(*args, **kwargs)

    def print_banner(self, text: str) -> None:
        """Print styled banner text."""
        self.console.print(text, style="bold bright_cyan")

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[bright_green]✔[/] {message}")

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[bright_red]✖[/] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[bright_yellow]![/] {message}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[bright_blue]→[/] {message}")

    # =========================================================================
    # Event Management
    # =========================================================================

    def add_event(
        self,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add and display a new event.

        Args:
            event_type: Category of event (session, beacon, command, etc.)
            message: Human-readable event description
            details: Optional additional event metadata
        """
        event = Event(event_type, message, details)
        self.events.append(event)
        self.stats["last_activity"] = event.timestamp

        # Print event to console
        with self._print_lock:
            self.console.print(event.to_rich())

    def add_session_event(self, host: str, ip: str, os: str) -> None:
        """Log a new session connection event."""
        event = EventFactory.session_connect(host, ip, os)
        self.events.append(event)
        self.stats["last_activity"] = event.timestamp
        with self._print_lock:
            self.console.print(event.to_rich())

    def add_beacon_event(self, host: str, ip: str, os: str, uuid: str) -> None:
        """Log a new beacon connection event."""
        event = EventFactory.beacon_connect(host, ip, os, uuid)
        self.events.append(event)
        self.stats["last_activity"] = event.timestamp
        with self._print_lock:
            self.console.print(event.to_rich())

    def add_beacon_checkin(self, host: str, ip: str, uuid: str) -> None:
        """Log a beacon check-in event."""
        event = EventFactory.beacon_checkin(host, ip, uuid)
        self.events.append(event)
        self.stats["last_activity"] = event.timestamp
        with self._print_lock:
            self.console.print(event.to_rich())

    def add_command_event(
        self, command: str, target: str, status: str = "sent"
    ) -> None:
        """
        Log a command event.

        Args:
            command: Command string
            target: Target session/beacon identifier
            status: Command status ("sent", "output", "error")
        """
        if status == "sent":
            event = EventFactory.command_sent(command, target)
        elif status == "output":
            event = EventFactory.command_output(command, target)
        else:
            event = EventFactory.command_error(command, target)

        self.events.append(event)
        self.stats["last_activity"] = event.timestamp
        with self._print_lock:
            self.console.print(event.to_rich())

    def add_disconnect_event(
        self, host: str, ip: str, conn_type: str = "Session"
    ) -> None:
        """Log a disconnection event."""
        event = EventFactory.session_disconnect(host, ip)
        if conn_type.lower() == "beacon":
            event = EventFactory.beacon_disconnect(host, ip)
        self.events.append(event)
        self.stats["last_activity"] = event.timestamp
        with self._print_lock:
            self.console.print(event.to_rich())

    # =========================================================================
    # Statistics Management
    # =========================================================================

    def update_stats(self, sessions: int, beacons: int) -> None:
        """Update connection statistics."""
        self.stats["sessions"] = sessions
        self.stats["beacons"] = beacons
        self.stats["total_connections"] = sessions + beacons

    def increment_commands(self) -> None:
        """Increment the commands executed counter."""
        self.stats["commands_executed"] += 1

    def _get_uptime_str(self) -> str:
        """Get formatted uptime string."""
        if not self.stats.get("server_uptime"):
            return "N/A"

        delta = datetime.now() - self.stats["server_uptime"]
        total_seconds = int(delta.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_stats_with_uptime(self) -> Dict[str, Any]:
        """Get stats dictionary with calculated uptime."""
        stats = self.stats.copy()
        stats["uptime"] = self._get_uptime_str()
        return stats

    # =========================================================================
    # Table Creation Methods (delegate to tables module)
    # =========================================================================

    def create_sessions_table(self, sessions: Dict) -> Any:
        """Create a modern styled sessions table."""
        return create_sessions_table(sessions)

    def create_beacons_table(self, beacons: Dict) -> Any:
        """Create a modern styled beacons table."""
        return create_beacons_table(beacons)

    def create_status_table(self) -> Any:
        """Create a compact status overview table."""
        return create_status_table(self.get_stats_with_uptime())

    def create_help_table(self, commands: Dict[str, str]) -> Any:
        """Create a modern help table."""
        return create_help_table(commands)

    def create_command_history_table(self, commands: List) -> Any:
        """Create a modern command history table."""
        return create_command_history_table(commands)

    def create_users_table(
        self, users: Dict, current_user_id: Optional[str] = None
    ) -> Any:
        """Create a modern styled users table."""
        return create_users_table(users, current_user_id)


# =============================================================================
# Module-Level Singleton and Convenience Functions
# =============================================================================

_ui_manager: Optional[UIManager] = None


def get_ui_manager() -> UIManager:
    """Get or create the singleton UIManager instance."""
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = UIManager()
    return _ui_manager


def log_connection_event(
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience function to log a connection event to the UI."""
    ui = get_ui_manager()
    ui.add_event(event_type, message, details)


def update_connection_stats(sessions: int, beacons: int) -> None:
    """Convenience function to update connection statistics."""
    ui = get_ui_manager()
    ui.update_stats(sessions, beacons)


def log_session_connect(host: str, ip: str, os: str) -> None:
    """Log a new session connection."""
    ui = get_ui_manager()
    ui.add_session_event(host, ip, os)


def log_beacon_connect(host: str, ip: str, os: str, uuid: str) -> None:
    """Log a new beacon connection."""
    ui = get_ui_manager()
    ui.add_beacon_event(host, ip, os, uuid)


def log_beacon_checkin(host: str, ip: str, uuid: str) -> None:
    """Log a beacon check-in."""
    ui = get_ui_manager()
    ui.add_beacon_checkin(host, ip, uuid)


def log_command(command: str, target: str, status: str = "sent") -> None:
    """Log a command event."""
    ui = get_ui_manager()
    ui.add_command_event(command, target, status)


def log_disconnect(host: str, ip: str, conn_type: str = "Session") -> None:
    """Log a disconnection event."""
    ui = get_ui_manager()
    ui.add_disconnect_event(host, ip, conn_type)
