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

        # Ensure command_data is always a dictionary
        if command_data is None:
            self.command_data = {}
        elif not isinstance(command_data, dict):
            # Convert non-dict data to dict format
            self.command_data = {"data": command_data}
        else:
            self.command_data = command_data

        # Log command data (truncate large payloads for readability)
        if (
            isinstance(self.command_data, dict)
            and "data" in self.command_data
            and isinstance(self.command_data["data"], (str, bytes))
            and len(self.command_data["data"]) > 100
        ):
            logger.debug(
                f"Command data (truncated): "
                f"{{... 'data': <{len(self.command_data['data'])} bytes> ...}}"
            )
        else:
            logger.debug(f"Command data: {self.command_data}")

    def __repr__(self) -> str:
        """Return a string representation of the beacon command."""
        return (
            f"beacon_command(uuid={self.command_uuid}, "
            f"beacon={self.beacon_uuid}, cmd={self.command}, "
            f"executed={self.executed})"
        )
