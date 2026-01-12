"""System Info plugin for beacon and session.

Retrieves system information from remote implants.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config, obfuscation_map
from ServerDatabase.database import DatabaseClass
from Modules.session.transfer import send_data, receive_data

from datetime import datetime
import json
from pathlib import Path


class SystemInfo:
    """Retrieve system information from beacon or session targets."""

    def __init__(self):
        self.command = "system_info"

        obfuscation: dict = {}
        try:
            obf_path = Path(__file__).with_name("obfuscate.json")
            with obf_path.open("r", encoding="utf-8") as f:
                obfuscation = json.load(f)
        except Exception as e:
            logger.error(f"SystemInfo: could not load obfuscate.json. Error: {e}")
            obfuscation = {}

        nested = obfuscation.get("system_info") or {}
        self.obf_name = nested.get("obfuscation_name") if isinstance(nested, dict) else None

        if obfuscation:
            try:
                obfuscation_map.update(obfuscation)
            except Exception:
                pass

        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue system info command for a beacon."""
        add_beacon_command_list(beacon.userID, None, self.command, self.database, "")
        logger.debug(f"SystemInfo command added for beacon: {beacon.userID}")

    def session(self, session: dict) -> None:
        """Request system info from a live session."""
        logger.info(f"Requesting system info from {session['userID']}")
        send_data(session['conn'], self.command)
        data = receive_data(session['conn'])
        self.database.insert_entry(
            "SystemInfo",
            f'"{session["userID"]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"',
        )
        print(data)