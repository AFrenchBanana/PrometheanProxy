# ============================================================================
# Session Core Module
# ============================================================================
# This module contains the main Session class representing a persistent
# session connection with a client.
# ============================================================================

# Standard Library Imports
import ssl
from typing import Tuple

# Third-Party Imports
import colorama

# Local Module Imports
from ServerDatabase.database import DatabaseClass

from ..global_objects import logger
from ..utils.console import cprint
from ..utils.ui_manager import RichPrint

# Import command handlers
from .commands.control_commands import ControlCommands


class Session(ControlCommands):
    """
    Represents a session with a connected client.

    Sessions are persistent connections that allow real-time interaction
    with connected clients. Unlike beacons, sessions maintain an active
    connection for immediate command execution.

    Inherits from:
        ControlCommands: Provides control command functionality

    Attributes:
        address: Tuple of (IP, port) for the connected client
        details: SSL socket connection object
        hostname: Hostname of the connected client
        operating_system: Operating system of the connected client
        mode: Mode of the session (e.g., interactive, beacon)
        loaded_modules: List of loaded modules for this session
        config: Configuration dictionary for database and settings
        database: Database instance for storing session data
        loaded_this_instant: Flag indicating if session was just created
    """

    def __init__(
        self,
        address: Tuple[str, int],
        details: ssl.SSLSocket,
        hostname: str,
        operating_system: str,
        mode: str,
        modules: list,
        config: dict,
        from_db: bool = False,
    ):
        """
        Initialize a new Session instance.

        Args:
            address: Tuple of (IP, port) for the connected client
            details: SSL socket connection object
            hostname: Hostname of the connected client
            operating_system: Operating system of the connected client
            mode: Mode of the session (e.g., interactive, beacon)
            modules: List of loaded modules for this session
            config: Configuration dictionary for database and settings
            from_db: Whether the session is being loaded from the database
        """
        self.address = address
        self.details = details
        self.hostname = hostname
        self.operating_system = operating_system
        self.mode = mode
        self.loaded_modules = modules
        self.config = config
        self.loaded_this_instant = False

        if not from_db:
            self.loaded_this_instant = True

        self.database = DatabaseClass(config, "command_database")
        colorama.init(autoreset=True)

        if not from_db:
            # Check if persistent sessions are enabled in config
            persist_sessions = config.get("command_database", {}).get(
                "persist_sessions", True
            )
            if persist_sessions:
                # Convert address tuple to string format "ip:port"
                address_str = f"{self.address[0]}:{self.address[1]}"
                # Socket objects cannot be stored in database, use empty string
                details_str = ""

                self.database.insert_entry(
                    "sessions",
                    (
                        address_str,
                        details_str,
                        self.hostname,
                        self.operating_system,
                        self.mode,
                        str(self.loaded_modules),
                    ),
                )
            else:
                logger.debug(
                    f"Session {self.address}: Not persisting to database "
                    "(persist_sessions=False)"
                )

        logger.info(
            f"New session created: {self.address[0]}:{self.address[1]} "
            f"({self.hostname})"
        )

        if not from_db:
            # Log to terminal via RichPrint for live UI update
            RichPrint.r_print(
                f"[bright_green]🔗[/] New session: [bright_green]{self.hostname}[/] "
                f"({self.address[0]}) - {self.operating_system}"
            )
        else:
            cprint(
                f"\nNew Session from {self.hostname} ({self.address[0]})", fg="green"
            )

    def __repr__(self) -> str:
        """Return a string representation of the session."""
        return (
            f"Session(address={self.address}, hostname={self.hostname}, "
            f"os={self.operating_system}, mode={self.mode})"
        )
