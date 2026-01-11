# Modules/session/session.py

import ssl
from typing import Tuple
import colorama
from ..utils.console import cprint
from ServerDatabase.database import DatabaseClass
from ..global_objects import sessions_list, logger

# Import command handlers
from .commands.control_commands import ControlCommands


class Session(ControlCommands):
    """
    Represents a session with a connected client.
    Args:
        address (Tuple[str, int]): The address of the connected client
        details (ssl.SSLSocket): The SSL socket connection object
        hostname (str): The hostname of the connected client
        operating_system (str): The operating system of the connected client
        mode (str): The mode of the session (e.g., interactive, beacon)
        modules (list): List of loaded modules for this session
        config (dict): Configuration object for database and settings
    Returns:
        None
    """
    def __init__(
        self,
        address,
        details,
        hostname,
        operating_system,
        mode,
        modules,
        config,
        from_db=False
    ):
        self.address = address
        self.details = details
        self.hostname = hostname
        self.operating_system = operating_system
        self.mode = mode
        self.loaded_modules = modules
        self.config = config
        if not from_db:
            self.loaded_this_instant = True
        self.database = DatabaseClass(config, "command_database")
        colorama.init(autoreset=True)

        if not from_db:
            # Check if persistent sessions are enabled in config
            persist_sessions = config.get("command_database", {}).get("persist_sessions", True)
            if persist_sessions:
                self.database.insert_entry(
                    "sessions",
                    [
                        self.address,
                        self.details,
                        self.hostname,
                        self.operating_system,
                        self.mode,
                        str(self.loaded_modules)
                    ])
            else:
                logger.debug(f"Session {self.address}: Not persisting to database (persist_sessions=False)")
        
        logger.info(
            f"New session created: {self.address[0]}:{self.address[1]} ({self.hostname})"
        )
        cprint(f"\nNew Session from {self.hostname} ({self.address[0]})", fg="green")


def add_connection_list(
    conn: ssl.SSLSocket,
    r_address: Tuple[str, int],
    host: str,
    operating_system: str,
    user_id: str,
    mode: str,
    modules: list,
    config,
    from_db=False
) -> None:
    """Adds a new session to the global sessions dictionary.
    Args:
        conn (ssl.SSLSocket): The SSL socket connection object
        r_address (Tuple[str, int]): The address of the connected client
        host (str): The hostname of the connected client
        operating_system (str): The operating system of the connected client
        user_id (str): The unique identifier for the session
        mode (str): The mode of the session (e.g., interactive, beacon)
        modules (list): List of loaded modules for this session
        config (dict): Configuration object for database and settings
        from_db (bool): Whether the session is being loaded from the database
    Returns:
        None
    """
    from Modules.utils.ui_manager import log_connection_event, update_connection_stats
    from Modules.global_objects import sessions_list, beacon_list

    logger.info(f"Adding connection {r_address[0]} ({host}) to sessions list.")
    new_session = Session(r_address, conn, host, operating_system, mode, modules, config, from_db=from_db)
    sessions_list[user_id] = new_session
    
    # Log the new session connection
    if not from_db:
        log_connection_event(
            "session",
            f"New session from {host} ({r_address[0]}) - {operating_system}",
            {"host": host, "ip": r_address[0], "os": operating_system, "mode": mode}
        )
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))


def remove_connection_list(r_address: Tuple[str, int]) -> None:
    """Removes a session from the global sessions dictionary based on address.
    Args:
        r_address (Tuple[str, int]): The address of the connected client to
            remove
    Returns:
        None
    """
    from Modules.utils.ui_manager import log_connection_event, update_connection_stats
    from Modules.global_objects import sessions_list, beacon_list

    key_to_remove = None
    for key, session_obj in sessions_list.items():
        if session_obj.address == r_address:
            key_to_remove = key
            break
            
    if key_to_remove:
        session_info = sessions_list[key_to_remove]
        log_connection_event(
            "disconnect",
            f"Session disconnected: {session_info.hostname} ({r_address[0]})",
            {"host": session_info.hostname, "ip": r_address[0]}
        )
        sessions_list.pop(key_to_remove)
        logger.info(f"Removed session {r_address[0]} from list.")
    else:
        logger.warning(f"Could not find session with address {r_address} to remove.")       