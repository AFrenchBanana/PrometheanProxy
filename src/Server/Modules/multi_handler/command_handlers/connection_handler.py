# ============================================================================
# Connection Handler Module
# ============================================================================
# This module provides connection management commands for the multi-handler,
# including listing connections, connecting to sessions, and closing connections.
# ============================================================================

# Standard Library Imports
import readline
import socket
import time

# Third-Party Imports
import colorama
from rich.table import Table
from rich import box

# Local Module Imports
from ...utils.ui_manager import get_ui_manager
from ...session.transfer import send_data, receive_data
from ...session.session import remove_connection_list
from ...beacon.beacon import remove_beacon_list
from ...global_objects import (
    sessions_list,
    beacon_list,
    multiplayer_connections,
    logger,
    tab_completion
)
from ...utils.console import cprint, warn, error as c_error


# ============================================================================
# ConnectionHandler Class
# ============================================================================


class ConnectionHandler:
    """
    Handles connection-related commands for the multi-handler module.
    
    Provides methods for listing active connections, connecting to sessions,
    and closing individual or all connections.
    """

    # ========================================================================
    # Connection Listing Methods
    # ========================================================================


    # ========================================================================
    # Connection Listing Methods
    # ========================================================================

    def listconnections(self) -> None:
        """
        List all active connections including sessions and beacons.
        
        Displays formatted tables showing details of active sessions, beacons,
        and multiplayer connections (if enabled). Includes timing information
        for beacons and status indicators.
        """
        # ----------------------------------------------------------------
        # Display Active Sessions
        # ----------------------------------------------------------------
        logger.info("Listing all active connections")
        if len(sessions_list) == 0:
            c_error("No Active Sessions")
        else:
            logger.info("Creating sessions table")
            
            session_table = Table(
                title="Active Sessions", 
                box=box.ROUNDED, 
                header_style="bold bright_cyan",
                border_style="bright_blue"
            )
            session_table.add_column("UUID", style="cyan")
            session_table.add_column("Hostname", style="white")
            session_table.add_column("Address", style="green")
            session_table.add_column("OS", style="yellow")
            
            for userID, session in sessions_list.items():
                session_table.add_row(
                    str(userID),
                    str(session.hostname),
                    str(session.address),
                    str(session.operating_system)
                )
                
            logger.info("Printing sessions table")
            get_ui_manager().console.print(session_table)

        # ----------------------------------------------------------------
        # Display Active Beacons
        # ----------------------------------------------------------------
        if len(beacon_list) == 0:
            logger.info("No active beacons found")
            c_error("No Active Beacons")
        else:
            beacon_table = Table(
                title="Active Beacons",
                box=box.ROUNDED,
                header_style="bold bright_cyan",
                border_style="bright_blue"
            )
            beacon_table.add_column("Host", style="white")
            beacon_table.add_column("OS", style="white")
            beacon_table.add_column("IP", style="green")
            beacon_table.add_column("ID", style="cyan")
            beacon_table.add_column("Last Callback")
            beacon_table.add_column("Status")
            beacon_table.add_column("Notes", style="italic dim")

            for userID, beacon in beacon_list.items():
                row_base = [
                    str(beacon.hostname),
                    str(beacon.operating_system),
                    str(beacon.address),
                    str(beacon.uuid),
                    str(beacon.last_beacon)
                ]
                
                status_text = ""
                notes_text = ""
                row_style = "white"
                
                # Calculate beacon timing status
                try:
                    next_beacon_time = time.strptime(
                        beacon.next_beacon, "%a %b %d %H:%M:%S %Y"
                    )
                    current_time = time.strptime(
                        time.asctime(), "%a %b %d %H:%M:%S %Y"
                    )

                    if time.mktime(current_time) > time.mktime(next_beacon_time):
                        # Beacon is late
                        time_diff = (
                            time.mktime(current_time) -
                            time.mktime(next_beacon_time)
                        )
                        if time_diff < beacon.jitter:
                            status_text = (
                                f"Expected Callback was {beacon.next_beacon}. "
                                f"It is {int(time_diff)} seconds late. (Within Jitter)"
                            )
                            row_style = "yellow"
                        else:
                            status_text = (
                                f"Expected Callback was {beacon.last_beacon}. "
                                f"It is {int(time_diff)} seconds late"
                            )
                            row_style = "red"
                    else:
                        # Beacon is on time
                        time_until = (
                            int(time.mktime(next_beacon_time) -
                                time.mktime(current_time))
                        )
                        status_text = (
                            f"Next Callback expected {beacon.next_beacon} "
                            f"in {time_until} seconds"
                        )
                        row_style = "white" # default or green
                except (ValueError, TypeError):
                    status_text = "Awaiting first call"
                    row_style = "white"
                    logger.error(
                        f"Error parsing next beacon time for {beacon.hostname}"
                    )
                
                # Mark beacons loaded from database
                if not beacon.loaded_this_instant:
                    row_style = "cyan"
                    notes_text = "This beacon has not yet loaded this instant."
                
                beacon_table.add_row(*row_base, status_text, notes_text, style=row_style)

            get_ui_manager().console.print(beacon_table)
        
        # ----------------------------------------------------------------
        # Display Multiplayer Connections (if enabled)
        # ----------------------------------------------------------------
        try:
            multiplayer_enabled = self.config["multiplayer"]["multiplayerEnabled"]
        except KeyError:
            multiplayer_enabled = False

        if multiplayer_enabled:
            if not multiplayer_connections:
                c_error("No Active Multiplayer Connections")
            else:
                cprint("Active Multiplayer Connections:", fg="white")
                for username, client in multiplayer_connections.items():
                    try:
                        addr = (
                            client.address[0]
                            if isinstance(client.address, (list, tuple))
                            else str(client.address)
                        )
                    except Exception:
                        addr = "unknown"
                    cprint(f"User: {username}, Address: {addr}", fg="white")

    # ========================================================================
    # Session Connection Methods
    # ========================================================================

    def sessionconnect(self) -> None:
        """
        Connect to a session from the list of active sessions.
        
        Prompts the user to select a session (if multiple exist) and
        establishes an interactive session with the selected client.
        """
        try:
            keys = list(sessions_list.keys())
            if not keys:
                c_error("No active sessions to connect to.")
                return

            if len(sessions_list) == 1:
                logger.info("Only one session available, connecting to it")
                session_id = keys[0]
            else:
                logger.info("Multiple sessions available, prompting user for selection")
                for i, session_id in enumerate(keys):
                    session = sessions_list[session_id]
                    print(
                        f"[{i}] {session_id} - {session.hostname} "
                        f"({session.address[0]})"
                    )
                choice = int(input("What client index? "))
                session_id = keys[choice]
            
            session = sessions_list[session_id]
            self.current_client_session(
                session.details,
                session.address,
                session_id
            )

        except (IndexError, ValueError):
            logger.error("Invalid client selection or no active sessions")
            cprint("Not a Valid Client", fg="white", bg="red")
        return

    # ========================================================================
    # Connection Closure Methods
    # ========================================================================

    def close_all_connections(self) -> None:
        """
        Close all active connections.
        
        Iterates through all active sessions and sends shutdown commands,
        then clears the session list. Beacons are handled separately.
        """
        logger.info("Closing all connections")
        error = False
        
        # Iterate over a copy of the list to avoid modification issues
        for conn in list(sessions_list.values()):
            try:
                send_data(conn.details, "shutdown")
                logger.info(f"Sent shutdown command to {conn.address}")
                if receive_data(conn.details) == "ack":
                    conn.details.shutdown(socket.SHUT_RDWR)
                    conn.details.close()
                    logger.info(f"Closed connection to {conn.address}")
                if not self.config["server"]["quiet_mode"]:
                    cprint(f"Closed {conn.address}", bg="green")
            except Exception as e:
                logger.error(f"Error closing connection {conn.address}: {e}")
                cprint(f"Error Closing + {conn.address}: {e}", bg="red")
                error = True
        
        logger.info("Clearing session and beacon lists")
        sessions_list.clear()  # Beacons are handled separately if they persist
        
        if not error:
            logger.info("All connections closed successfully")
            cprint("All connections closed", bg="green")
        else:
            logger.error("Not all connections could be closed")
            cprint("Not all connections could be closed", bg="red")
        return

    def close_from_multihandler(self) -> None:
        """
        Close an individual connection from the multi-handler.
        
        Prompts the user to specify a UUID and closes either a session or
        queues a close command for a beacon.
        """
        logger.info("Closing individual client from multi handler")
        try:
            all_keys = list(sessions_list.keys()) + list(beacon_list.keys())
            if not all_keys:
                c_error("No connections to close.")
                return

            readline.set_completer(
                lambda text, state: tab_completion(text, state, all_keys)
            )
            uuid_to_close = input("What client UUID do you want to close? ")
            logger.info(f"User wants to close client with UUID: {uuid_to_close}")

            if uuid_to_close in sessions_list:
                session = sessions_list[uuid_to_close]
                session.close_connection(session.details, session.address)
                # The close_connection method should handle list removal
                cprint(f"Session {uuid_to_close} Closed", bg="green")

            elif uuid_to_close in beacon_list:
                logger.info(f"Queueing close command for beacon with ID: {uuid_to_close}")
                beacon = beacon_list[uuid_to_close]
                beacon.close_connection(uuid_to_close)  # This should queue the command
                cprint(
                    f"Beacon {uuid_to_close} will shutdown at next callback.",
                    bg="green"
                )
            else:
                cprint("Not a valid connection UUID.", bg="red")

        except (ValueError, IndexError) as e:
            logger.error(f"Error during close operation: {e}")
            cprint("An error occurred.", bg="red")
        return