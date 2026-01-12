"""Template plugin for beacon and session.

Copy this file as a starting point for new plugins.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config, obfuscation_map
from ServerDatabase.database import DatabaseClass
from Modules.session.transfer import send_data, receive_data

from datetime import datetime
import json
from pathlib import Path


class Template:
    """Template plugin - copy and modify for new plugins."""

    def __init__(self):
        self.command = "template"

        obfuscation: dict = {}
        try:
            obf_path = Path(__file__).with_name("obfuscate.json")
            with obf_path.open("r", encoding="utf-8") as f:
                obfuscation = json.load(f)
        except Exception as e:
            logger.error(f"Template: could not load obfuscate.json. Error: {e}")
            obfuscation = {}

        nested = obfuscation.get("template") or {}
        self.obf_name = nested.get("obfuscation_name") if isinstance(nested, dict) else None

        if obfuscation:
            try:
                obfuscation_map.update(obfuscation)
            except Exception:
                pass

        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue template command for a beacon."""
        add_beacon_command_list(beacon.userID, None, self.command, self.database, "")
        logger.debug(f"Template command added for beacon: {beacon.userID}")

    def session(self, session: dict) -> None:
        """Request template data from a live session."""
        logger.info(f"Requesting template from {session['userID']}")
        send_data(session['conn'], self.command)
        data = receive_data(session['conn'])
        self.database.insert_entry(
            "Template",
            f'"{session["userID"]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"',
        )
        print(data)