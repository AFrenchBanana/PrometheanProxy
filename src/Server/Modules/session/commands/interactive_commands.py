# Modules/session/commands/interactive_commands.py

import ssl
from typing import Tuple
from datetime import datetime
from ..transfer import send_data, receive_data
from ...global_objects import logger

class InteractiveCommands:
    """Handles interactive session commands."""

    def shell(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Runs a shell between the session's client and server."""
        logger.info(f"Starting shell session with {r_address[0]}:{r_address[1]}")
        print(f"Shell session started with {r_address[0]}. Type 'exit' to quit.")
        send_data(conn, "shell")
        
        details = receive_data(conn)
        username, cwd = details.split("<sep>")
        
        while True:
            command = input(f"{username}@{r_address[0]}-[{cwd}]$ ")
            if not command.strip(): continue

            send_data(conn, command)
            if command.lower() == "exit": break

            output = receive_data(conn)
            results, _, cwd = output.rpartition("<sep>")
            
            self.database.insert_entry(
                "Shell", f"'{r_address[0]}', '{datetime.now()}', '{command.replace("'", "''")}', '{results.replace("'", "''")}'"
            )
            print(results)
        return

    def list_dir(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Lists a directory on the client."""
        logger.info(f"Listing directory for {r_address[0]}:{r_address[1]}")
        send_data(conn, "list_dir")
        
        directory_to_list = input("What directory do you want to list?: ")
        send_data(conn, directory_to_list)
        
        directory_listing = receive_data(conn)
        logger.info(f"Received directory listing for '{directory_to_list}' from {r_address[0]}")

        if str(directory_listing).startswith("Error:"):
            logger.error(f"Error listing directory '{directory_to_list}': {directory_listing}")
        else:
            try:
                self.database.insert_entry(
                    "Shell", f"'{r_address[0]}', '{datetime.now()}', 'ls {directory_to_list}', '{directory_listing.replace("'", "''")}'"
                )
            except Exception as e:
                logger.error(f"Error inserting directory listing into database: {e}")
        print(directory_listing)