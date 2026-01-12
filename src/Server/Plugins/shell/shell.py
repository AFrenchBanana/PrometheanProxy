"""Shell plugin for beacon and session.

Provides shell command execution on remote implants.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config
from ServerDatabase.database import DatabaseClass


class Shell:
    """Execute shell commands on beacon or session targets."""

    def __init__(self):
        self.command = "shell"
        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue shell command for a beacon."""
        command = input("What command do you want to run: ")
        add_beacon_command_list(beacon.userID, None, self.command, self.database, command)
        logger.debug(f"Shell command added for beacon: {beacon.userID}")

    def session(self, session: dict) -> None:
        """Execute shell command on a live session."""
        print("Not implemented")
        return