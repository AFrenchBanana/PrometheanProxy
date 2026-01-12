# ============================================================================
# Beacon Registry Module
# ============================================================================
# This module provides global functions for managing the beacon registry,
# including adding, removing, and tracking beacons and their queued commands.
# ============================================================================

# Standard Library Imports
import uuid

# Local Module Imports
from ..global_objects import beacon_list, command_list, logger


class beacon_command:
    """
    Represents a queued command for a beacon to execute.

    Attributes:
        command_uuid: Unique identifier for this command
        beacon_uuid: UUID of the beacon this command is for
        command: Command string to execute
        command_output: Output returned from command execution
        executed: Boolean indicating if command has been executed
        command_data: Additional data payload for the command
    """

    def __init__(
        self, command_uuid, beacon_uuid, command, command_output, executed, command_data
    ):
        logger.debug(
            f"Creating beacon command: {command_uuid} for beacon: {beacon_uuid}"
        )
        self.command_uuid = command_uuid
        self.beacon_uuid = beacon_uuid
        self.command = command
        logger.debug(f"Command: {command}")
        self.command_output = command_output
        self.executed = executed
        self.command_data = command_data

        # Log command data (truncate large payloads for readability)
        if (
            isinstance(command_data, dict)
            and "data" in command_data
            and len(command_data["data"]) > 100
        ):
            logger.debug(
                f"Command data (truncated): "
                f"{{... 'data': <{len(command_data['data'])} bytes> ...}}"
            )
        else:
            logger.debug(f"Command data: {command_data}")


def add_beacon_list(
    beacon_uuid: str,
    r_address: str,
    hostname: str,
    operating_system: str,
    last_beacon: float,
    timer: float,
    jitter: int,
    config,
    database,
    modules=None,
    from_db=False,
) -> None:
    """
    Add a new beacon to the global beacon list.

    Creates a new Beacon instance and adds it to the global beacon_list
    dictionary for tracking and management.

    Args:
        beacon_uuid: Unique identifier for the beacon
        r_address: IP address of the beacon
        hostname: Hostname of the beacon
        operating_system: Operating system of the beacon
        last_beacon: Timestamp of last check-in
        timer: Check-in interval in seconds
        jitter: Jitter percentage for randomizing timing
        config: Configuration dictionary
        database: Database connection instance
        modules: List of loaded modules (default: ["shell", "close", "session"])
        from_db: Whether beacon is being loaded from database
    """
    from Modules.global_objects import beacon_list, sessions_list
    from Modules.utils.ui_manager import log_connection_event, update_connection_stats

    from .core import Beacon

    logger.debug(f"Adding beacon with UUID: {beacon_uuid}")
    logger.debug(f"Beacon address: {r_address}")
    logger.debug(f"Beacon hostname: {hostname}")
    logger.debug(f"Beacon operating system: {operating_system}")
    logger.debug(f"Beacon last beacon: {last_beacon}")
    logger.debug(f"Beacon timer: {timer}")
    logger.debug(f"Beacon jitter: {jitter}")

    if modules is None:
        modules = ["shell", "close", "session"]

    new_beacon = Beacon(
        beacon_uuid,
        r_address,
        hostname,
        operating_system,
        last_beacon,
        timer,
        jitter,
        modules,
        config,
        database,
        from_db=from_db,
    )
    beacon_list[beacon_uuid] = new_beacon

    # Log the new beacon connection
    if not from_db:
        log_connection_event(
            "beacon",
            f"New beacon from {hostname} ({r_address}) - {operating_system}",
            {
                "host": hostname,
                "ip": r_address,
                "os": operating_system,
                "timer": timer,
                "uuid": beacon_uuid,
            },
        )
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))


def add_beacon_command_list(
    beacon_uuid: str, cmd_uuid: str, command: str, database, command_data: dict = None
) -> None:
    """
    Queue a command for a beacon to execute.

    Creates a new beacon_command instance and adds it to the global command_list
    dictionary. Also persists the command to the database.

    Args:
        beacon_uuid: Unique identifier for the beacon
        cmd_uuid: Unique identifier for the command (auto-generated if None)
        command: Command string to execute
        database: Database connection instance
        command_data: Additional data payload for the command (optional)
    """
    if command_data is None:
        command_data = {}

    logger.debug(f"Adding command for beacon UUID: {beacon_uuid}")
    logger.debug(f"Command UUID: {cmd_uuid}")
    logger.debug(f"Command: {command}")

    # Log command data (truncate large payloads)
    if (
        isinstance(command_data, dict)
        and "data" in command_data
        and len(command_data["data"]) > 100
    ):
        logger.debug(
            f"Command data (truncated): "
            f"{{... 'data': <{len(command_data['data'])} bytes> ...}}"
        )
    else:
        logger.debug(f"Command data: {command_data}")

    # Generate UUID if not provided
    if not cmd_uuid or cmd_uuid == "":
        cmd_uuid = str(uuid.uuid4())
        logger.debug(f"Generated new command UUID: {cmd_uuid}")

    # Create command instance
    new_command = beacon_command(
        cmd_uuid, beacon_uuid, command, "", False, command_data
    )

    # Persist to database
    database.insert_entry(
        "beacon_commands",
        [command, cmd_uuid, beacon_uuid, str(command_data), False, "Awaiting Response"],
    )

    logger.debug(f"New command created: {new_command}")
    command_list[cmd_uuid] = new_command


def remove_beacon_list(beacon_uuid: str) -> None:
    """
    Remove a beacon from the global beacon list.

    Removes the beacon with the specified UUID from the beacon_list dictionary.

    Args:
        beacon_uuid: Unique identifier for the beacon to remove
    """
    from Modules.global_objects import sessions_list
    from Modules.utils.ui_manager import (
        RichPrint,
        log_disconnect,
        update_connection_stats,
    )

    logger.debug(f"Removing beacon with UUID: {beacon_uuid}")
    if beacon_uuid in beacon_list:
        beacon = beacon_list[beacon_uuid]
        # Log disconnection to live events panel
        log_disconnect(beacon.hostname, beacon.address, "Beacon")
        RichPrint.r_print(
            f"[bright_red]❌[/] Beacon disconnected: "
            f"[dim]{beacon.hostname}[/] ({beacon.address})"
        )
        beacon_list.pop(beacon_uuid)
        logger.debug(f"Beacon {beacon_uuid} removed from beacon list")
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))
    else:
        print(f"Beacon {beacon_uuid} not found in beacon list")
        logger.warning(f"Beacon {beacon_uuid} not found in beacon list")
    logger.debug(f"Beacon list after removal: {beacon_list.keys()}")
