# ============================================================================
# Beacon Command Module
# ============================================================================
# This module defines the beacon_command class representing a queued command
# for a beacon to execute.
# ============================================================================

from ..global_objects import logger


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
        self,
        command_uuid: str,
        beacon_uuid: str,
        command: str,
        command_output: str,
        executed: bool,
        command_data: dict,
    ):
        """
        Initialize a new beacon command.

        Args:
            command_uuid: Unique identifier for this command
            beacon_uuid: UUID of the beacon this command is for
            command: Command string to execute
            command_output: Output returned from command execution
            executed: Boolean indicating if command has been executed
            command_data: Additional data payload for the command
        """
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

    def __repr__(self) -> str:
        """Return a string representation of the beacon command."""
        return (
            f"beacon_command(uuid={self.command_uuid}, "
            f"beacon={self.beacon_uuid}, cmd={self.command}, "
            f"executed={self.executed})"
        )
