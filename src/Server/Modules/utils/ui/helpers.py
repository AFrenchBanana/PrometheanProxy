"""
UI Helpers Module - Utility Functions and Classes

Provides helper functions, context managers, and utility classes
for the PrometheanProxy terminal interface.
"""

import io
import sys
from typing import Any, Optional


class Capture:
    """
    Context manager to capture stdout/stderr output.

    Useful for capturing output from functions that print directly
    to stdout/stderr, allowing the output to be processed or redirected.

    Example:
        with Capture() as cap:
            print("Hello, World!")
        captured_text = cap.stdout.getvalue()
    """

    def __init__(self) -> None:
        """Initialize the capture buffers."""
        self.stdout: io.StringIO = io.StringIO()
        self.stderr: io.StringIO = io.StringIO()
        self._old_stdout: Optional[Any] = None
        self._old_stderr: Optional[Any] = None

    def __enter__(self) -> "Capture":
        """Enter the context and start capturing output."""
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Exit the context and restore original stdout/stderr."""
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr

    def get_stdout(self) -> str:
        """Get captured stdout content."""
        return self.stdout.getvalue()

    def get_stderr(self) -> str:
        """Get captured stderr content."""
        return self.stderr.getvalue()

    def get_all(self) -> str:
        """Get all captured output (stdout + stderr)."""
        return self.stdout.getvalue() + self.stderr.getvalue()


class RichPrint:
    """
    Static class for terminal output that integrates with the UI manager.

    Provides convenient class methods for printing styled output
    to the terminal through the centralized UI manager.
    """

    @classmethod
    def r_print(cls, *args, **kwargs) -> None:
        """
        Print to the terminal using the UI manager.

        Args:
            *args: Positional arguments passed to console.print()
            **kwargs: Keyword arguments passed to console.print()
        """
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.print(*args, **kwargs)

    @classmethod
    def clear(cls) -> None:
        """Clear the terminal screen."""
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.console.clear()

    @classmethod
    def success(cls, message: str) -> None:
        """Print a success message."""
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.print_success(message)

    @classmethod
    def error(cls, message: str) -> None:
        """Print an error message."""
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.print_error(message)

    @classmethod
    def warning(cls, message: str) -> None:
        """Print a warning message."""
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.print_warning(message)

    @classmethod
    def info(cls, message: str) -> None:
        """Print an info message."""
        from .manager import get_ui_manager

        ui = get_ui_manager()
        ui.print_info(message)


def format_bytes(num_bytes: int) -> str:
    """
    Format a byte count as a human-readable string.

    Args:
        num_bytes: Number of bytes to format

    Returns:
        Human-readable string (e.g., "1.5 MB", "256 KB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string (e.g., "2h 30m", "45s")
    """
    if seconds < 0:
        return "N/A"

    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        if secs > 0:
            return f"{minutes}m {secs}s"
        return f"{minutes}m"

    hours = minutes // 60
    mins = minutes % 60

    if hours < 24:
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"

    days = hours // 24
    hrs = hours % 24

    if hrs > 0:
        return f"{days}d {hrs}h"
    return f"{days}d"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length with a suffix.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncating (default: "...")

    Returns:
        Truncated string or original if within limits
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_uuid(uuid: str, max_length: int = 12) -> str:
    """
    Format a UUID for display, truncating if needed.

    Args:
        uuid: UUID string to format
        max_length: Maximum length before truncation

    Returns:
        Formatted UUID string
    """
    if len(uuid) <= max_length:
        return uuid
    return uuid[:max_length] + "..."


def format_ip_address(address: Any) -> str:
    """
    Format an address (tuple or string) for display.

    Args:
        address: Address as tuple (ip, port) or string

    Returns:
        Formatted IP address string
    """
    if isinstance(address, tuple):
        return address[0]
    return str(address)


def colorize_status(status: bool) -> str:
    """
    Return a Rich-formatted status string.

    Args:
        status: Boolean status value

    Returns:
        Rich markup string with colored status
    """
    if status:
        return "[bright_green]✔ Active[/]"
    return "[bright_red]✖ Inactive[/]"


def colorize_bool(value: bool) -> str:
    """
    Return a Rich-formatted boolean string.

    Args:
        value: Boolean value

    Returns:
        Rich markup string with colored boolean
    """
    if value:
        return "[bright_green]✔ True[/]"
    return "[bright_red]✖ False[/]"


def make_table_row_style(idx: int) -> str:
    """
    Get alternating row style for tables.

    Args:
        idx: Row index (0-based)

    Returns:
        Style string for the row
    """
    return "" if idx % 2 == 0 else "dim"
