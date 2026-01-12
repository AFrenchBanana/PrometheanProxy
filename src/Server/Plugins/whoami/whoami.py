"""Whoami plugin for beacon and session.

Retrieves current user information from remote implants.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config, obfuscation_map
from ServerDatabase.database import DatabaseClass
from Modules.session.transfer import send_data, receive_data

from datetime import datetime
import json
from pathlib import Path


class Whoami:
    """Retrieve current user information from beacon or session targets."""

    def __init__(self):
        self.command = "whoami"

        obfuscation: dict = {}
        try:
            obf_path = Path(__file__).with_name("obfuscate.json")
            with obf_path.open("r", encoding="utf-8") as f:
                obfuscation = json.load(f)
        except Exception as e:
            logger.error(f"Whoami: could not load obfuscate.json. Error: {e}")

        if obfuscation:
            try:
                obfuscation_map.update(obfuscation)
            except Exception:
                pass

        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue whoami command for a beacon."""
        add_beacon_command_list(beacon.userID, None, self.command, self.database, "")
        logger.debug(f"Whoami command added for beacon: {beacon.userID}")

    def session(self, session: dict) -> None:
        """Request whoami from a live session."""
        logger.info(f"Requesting whoami from {session['userID']}")
        send_data(session['conn'], self.command)
        data = receive_data(session['conn'])
        self.database.insert_entry(
            "Whoami",
            f'"{session["userID"]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"',
        )
        print(data)
