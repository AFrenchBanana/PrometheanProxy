# ============================================================================
# Session Registry Module
# ============================================================================
# This module provides global functions for managing the session registry,
# including adding and removing sessions from the global sessions list.
# ============================================================================

# Standard Library Imports
import ssl
from typing import Tuple

# Local Module Imports
from ..global_objects import beacon_list, logger, sessions_list
from ..utils.ui_manager import (
    RichPrint,
    log_disconnect,
    log_session_connect,
    update_connection_stats,
)


def add_connection_list(
    conn: ssl.SSLSocket,
    r_address: Tuple[str, int],
    host: str,
    operating_system: str,
    user_id: str,
    mode: str,
    modules: list,
    config,
    from_db=False,
) -> None:
    """
    Add a new session to the global sessions dictionary.

    Creates a new Session instance and adds it to the global sessions_list
    dictionary for tracking and management.

    Args:
        conn: The SSL socket connection object
        r_address: The address of the connected client (host, port)
        host: The hostname of the connected client
        operating_system: The operating system of the connected client
        user_id: The unique identifier for the session
        mode: The mode of the session (e.g., interactive, beacon)
        modules: List of loaded modules for this session
        config: Configuration object for database and settings
        from_db: Whether the session is being loaded from the database
    """
    from Modules.global_objects import beacon_list, sessions_list

    from .core import Session

    logger.info(f"Adding connection {r_address[0]} ({host}) to sessions list.")
    new_session = Session(
        r_address, conn, host, operating_system, mode, modules, config, from_db=from_db
    )
    sessions_list[user_id] = new_session

    # Log the new session connection to live events panel
    if not from_db:
        log_session_connect(host, r_address[0], operating_system)
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))


def remove_connection_list(r_address: Tuple[str, int]) -> None:
    """
    Remove a session from the global sessions dictionary based on address.

    Searches for and removes the session with the matching address from
    the sessions_list dictionary.

    Args:
        r_address: The address of the connected client to remove (host, port)
    """
    from Modules.global_objects import beacon_list, sessions_list

    key_to_remove = None
    for key, session_obj in sessions_list.items():
        if session_obj.address == r_address:
            key_to_remove = key
            break

    if key_to_remove:
        session_info = sessions_list[key_to_remove]
        # Log disconnection to live events panel
        log_disconnect(session_info.hostname, r_address[0], "Session")
        RichPrint.r_print(
            f"[bright_red]❌[/] Session disconnected: "
            f"[dim]{session_info.hostname}[/] ({r_address[0]})"
        )
        sessions_list.pop(key_to_remove)
        logger.info(f"Removed session {r_address[0]} from list.")
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))
    else:
        logger.warning(f"Could not find session with address {r_address} to remove.")
