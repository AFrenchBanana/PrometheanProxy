# ============================================================================
# Beacon Core Module
# ============================================================================
# This module contains the main Beacon class representing an asynchronous
# beacon connection that checks in periodically for commands.
# ============================================================================

# Standard Library Imports
import ast
import time
import traceback
from typing import TYPE_CHECKING, Union

# Third-Party Imports
import colorama

# Local Module Imports
if TYPE_CHECKING:
    from ServerDatabase.database import DatabaseClass

from ..global_objects import logger
from ..utils.file_manager import FileManagerClass
from .history import HistoryMixin
from .modules import ModulesMixin
from .registry import add_beacon_command_list, remove_beacon_list


class Beacon(HistoryMixin, ModulesMixin):
    """
    Represents an asynchronous beacon connection.

    Beacons check in periodically based on configured timer and jitter settings
    to retrieve queued commands and send execution results. Unlike sessions,
    beacons do not maintain persistent connections.

    Inherits from:
        HistoryMixin: Provides command history and configuration methods
        ModulesMixin: Provides module loading functionality

    Attributes:
        uuid: Unique identifier for this beacon
        database: Database connection instance
        file_manager: File manager for handling file operations
        address: IP address of the beacon
        hostname: Hostname of the beacon
        operating_system: Operating system of the beacon
        last_beacon: Timestamp of last check-in (human-readable)
        next_beacon: Expected timestamp of next check-in (human-readable)
        timer: Check-in interval in seconds
        jitter: Jitter percentage for randomizing check-in timing
        config: Configuration dictionary
        loaded_modules: List of modules loaded on this beacon
        loaded_this_instant: Flag indicating if beacon was just created
    """

    def __init__(
        self,
        uuid: str,
        address: str,
        hostname: str,
        operating_system: str,
        last_beacon: Union[str, float, int],
        timer: float,
        jitter: float,
        config: dict,
        database: "DatabaseClass" = None,
        modules: Union[str, list, None] = None,
        from_db: bool = False,
    ):
        """
        Initialize a new Beacon instance.

        Args:
            uuid: Unique identifier for the beacon
            address: IP address of the beacon
            hostname: Hostname of the beacon
            operating_system: Operating system of the beacon
            last_beacon: Timestamp of last check-in
            timer: Check-in interval in seconds
            jitter: Jitter percentage for randomizing timing
            modules: List of loaded modules
            config: Configuration dictionary
            database: Database connection instance (optional, uses shared if None)
            from_db: Whether beacon is being loaded from database
        """
        logger.debug(f"Creating beacon with UUID: {uuid}")
        self.uuid = uuid
        # Use shared database instance if none provided
        if database is None:
            from Modules import global_objects

            self.database = global_objects.get_database("command_database")
        else:
            self.database = database
        self.file_manager = FileManagerClass(config, uuid)
        self.address = address
        self.hostname = hostname
        self.operating_system = operating_system
        self.is_late = False

        # ----------------------------------------------------------------
        # Parse and Format Beacon Timing
        # ----------------------------------------------------------------
        lb_float = 0.0
        if isinstance(last_beacon, (float, int)):
            lb_float = float(last_beacon)
        elif isinstance(last_beacon, str):
            try:
                lb_float = time.mktime(
                    time.strptime(last_beacon, "%a %b %d %H:%M:%S %Y")
                )
            except ValueError:
                try:
                    lb_float = time.mktime(
                        time.strptime(last_beacon, "%Y-%m-%d %H:%M:%S")
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid last_beacon format: {last_beacon}. "
                        "Using current time."
                    )
                    lb_float = time.time()
        else:
            lb_float = time.time()

        self.last_beacon = time.asctime(time.localtime(lb_float))
        self.next_beacon = time.asctime(time.localtime(lb_float + timer))

        self.timer = timer
        self.jitter = jitter
        self.config = config

        # ----------------------------------------------------------------
        # Parse Modules List
        # ----------------------------------------------------------------
        if isinstance(modules, str):
            try:
                parsed = ast.literal_eval(modules)
                # Ensure the parsed result is a list
                if isinstance(parsed, list):
                    self.loaded_modules = parsed
                else:
                    logger.warning(
                        f"Parsed modules is not a list (got {type(parsed).__name__}): {modules}. "
                        "Defaulting to empty list."
                    )
                    self.loaded_modules = []
            except (ValueError, SyntaxError):
                logger.warning(
                    f"Failed to parse modules string: {modules}. "
                    "Defaulting to empty list."
                )
                self.loaded_modules = []
        elif isinstance(modules, list):
            self.loaded_modules = modules
        elif modules is None:
            self.loaded_modules = []
        else:
            # Handle any other type (bool, int, etc.) by converting to empty list
            logger.warning(
                f"Invalid modules type {type(modules).__name__}: {modules}. "
                "Defaulting to empty list."
            )
            self.loaded_modules = []

        # ----------------------------------------------------------------
        # Save to Database (if not loading from database)
        # ----------------------------------------------------------------
        self.loaded_this_instant = False
        if not from_db:
            self.loaded_this_instant = True
            # Check if persistent beacons are enabled in config
            persist_beacons = config.get("command_database", {}).get(
                "persist_beacons", True
            )
            if persist_beacons:
                self.database.insert_entry(
                    "connections",
                    [
                        self.uuid,
                        self.address,
                        self.hostname,
                        self.operating_system,
                        "beacon",  # connection_type
                        lb_float,  # last_seen
                        lb_float + timer,  # next_beacon
                        self.timer,
                        self.jitter,
                        str(self.loaded_modules),
                        None,  # session_address (null for beacons)
                        None,  # last_mode_switch (null on creation)
                        time.time(),  # created_at
                    ],
                )
            else:
                logger.debug(
                    f"Beacon {self.uuid}: Not persisting to database "
                    "(persist_beacons=False)"
                )

    # ========================================================================
    # Connection Management Methods
    # ========================================================================

    def close_connection(self, userID: str) -> None:
        """
        Close the beacon connection after user confirmation.

        Queues a shutdown command for the beacon and removes it from the
        active beacon list upon user confirmation.

        Args:
            userID: Unique identifier for the beacon
        """
        if (
            input(
                colorama.Back.RED + "Are you sure want to close the connection?: y/N "
            ).lower()
            == "y"
        ):
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + "Closing " + userID)

            try:
                logger.debug(f"Closing connection for beacon: {userID}")
                add_beacon_command_list(userID, None, "shutdown", self.database)

            except BaseException:  # handles ssl.SSLEOFError
                logger.error(f"Error closing connection for beacon: {userID}")
                if not self.config["server"]["quiet_mode"]:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()
                    logger.error(traceback.format_exc())
                pass

            logger.debug(f"Removing beacon from list: {userID}")
            remove_beacon_list(userID)
            print(colorama.Back.GREEN + "Closed")
        else:
            print(colorama.Back.GREEN + "Connection not closed")
        return

    # ========================================================================
    # Session Management Methods
    # ========================================================================

    def switch_session(self, userID: str) -> None:
        """
        Switch the beacon to session mode.

        Queues a command instructing the beacon to switch from asynchronous
        beacon mode to persistent session mode.

        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Switching session for userID: {userID}")
        add_beacon_command_list(userID, None, "session", self.database, {})
