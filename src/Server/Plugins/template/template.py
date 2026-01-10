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


class Template:
    def __init__(self):
        self.command = "template"

        obfuscation: dict = {}
        try:
            obf_path = Path(__file__).with_name("obfuscate.json")
            with obf_path.open("r", encoding="utf-8") as f:
                obfuscation = json.load(f)
        except Exception as e:
            logger.error(
                f"Netstat: could not load obfuscate.json (falling back to plain command). Error: {e}"
            )
            obfuscation = {}

      
        nested = obfuscation.get("netstat") or {}
        self.obf_name = nested.get("obfuscation_name") if isinstance(nested, dict) else None
      
        if obfuscation:
            try:
                obfuscation_map.update(obfuscation)
            except Exception:
                pass

        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue system info command for a beacon by userID."""
        add_beacon_command_list(beacon.userID, None, self.command, "")
        logger.debug(
            f"Template command added to command list for userID: {beacon.userID}"
        )

    def session(self, session: dict) -> None:
        """Request template from a live session and store the result."""
        logger.info(f"Requesting template from {session['userID']}")
        send_data(session['conn'], self.command)
        data = receive_data(session['conn'])
        self.database.insert_entry(
            "Template",
            f'"{session["userID"]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"',
        )
        print(data)