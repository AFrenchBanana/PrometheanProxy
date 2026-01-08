# Modules/multi_handler/command_handlers/connection_handler.py

# Corrected imports: pointing to the new 'transfer.py' for socket functions
from ...session.transfer import send_data, receive_data
from ...session.session import remove_connection_list

from ...beacon.beacon import remove_beacon_list
from ...global_objects import sessions_list, beacon_list, multiplayer_connections, logger, tab_completion
from ...utils.console import cprint, warn, error as c_error

from tabulate import tabulate
import colorama
import socket
import readline
import time


class ConnectionHandler:
    """
    Handles various connection-related commands for the multi-handler module.
    Args:
        None
    Returns:
        None
    """

    def listconnections(self) -> None:
        """
        Lists all active connections including sessions and beacons.
        Args:   
            None
        Returns:    
            None
        """
        # Sessions table
        logger.info("Listing all active connections")
        if len(sessions_list) == 0:
            c_error("No Active Sessions")
        else:
            print("Sessions:")
            table = []
            logger.info("Creating sessions table")
            for userID, session in sessions_list.items():
                table.append((userID, session.hostname, session.address, session.operating_system))
            logger.info("Printing sessions table")
            cprint(tabulate(
                table, headers=["UUID", "Hostname", "Address", "OS"],
                tablefmt="grid"), fg="white")

        # Beacons table
        if len(beacon_list) == 0:
            logger.info("No active beacons found")
            c_error("No Active Beacons")
        else:
            print("Beacons:")
            table = []
            for userID, beacon in beacon_list.items():
                row = [
                    beacon.hostname,
                    beacon.operating_system,
                    beacon.address,
                    beacon.uuid,
                    beacon.last_beacon
                ]
                try:
                    next_beacon_time = time.strptime(
                        beacon.next_beacon, "%a %b %d %H:%M:%S %Y")
                    current_time = time.strptime(
                        time.asctime(), "%a %b %d %H:%M:%S %Y")

                    if time.mktime(current_time) > time.mktime(
                            next_beacon_time):
                        time_diff = time.mktime(current_time) - time.mktime(
                            next_beacon_time)
                        if time_diff < beacon.jitter:
                            row.append(f"Expected Callback was {beacon.next_beacon}. It is {int(time_diff)} seconds late. (Within Jitter)") # noqa
                            row_color = colorama.Fore.YELLOW
                        else:
                            row.append(f"Expected Callback was {beacon.last_beacon}. It is {int(time_diff)} seconds late") # noqa
                            row_color = colorama.Fore.RED
                    else:
                        row.append(f"Next Callback expected {beacon.next_beacon} in {int(time.mktime(next_beacon_time) - time.mktime(current_time))} seconds") # noqa
                        row_color = colorama.Fore.WHITE
                except (ValueError, TypeError):
                    row.append("Awaiting first call")
                    row_color = colorama.Fore.WHITE
                    logger.error(
                        f"Error parsing next beacon time for {beacon.hostname}")
                table.append((row, row_color))

            # Print the table with color
            for row, row_color in table:
                # Map colorama Fore value to our helper fg names
                fg = "white"
                if row_color == colorama.Fore.RED:
                    fg = "red"
                elif row_color == colorama.Fore.YELLOW:
                    fg = "yellow"
                elif row_color == colorama.Fore.CYAN:
                    fg = "cyan"
                elif row_color == colorama.Fore.GREEN:
                    fg = "green"
                cprint(tabulate([row], headers=["Host", "OS", "IP", "ID",
                                               "Last Callback", "Status"],
                               tablefmt="grid"), fg=fg)
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
                        addr = client.address[0] if isinstance(client.address, (list, tuple)) else str(client.address)
                    except Exception:
                        addr = "unknown"
                    cprint(f"User: {username}, Address: {addr}", fg="white")

    def sessionconnect(self) -> None:
        """
        Connects to a session from the list of active sessions.
        Args:
            None
        Returns:    
            None        
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
                    print(f"[{i}] {session_id} - {session.hostname} ({session.address[0]})")
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

    def close_all_connections(self) -> None:
        """
        Closes all active connection.
        Args: 
            None
        Returns:    
            None
        """
        
        logger.info("Closing all connections")
        error = False
        # Iterate over a copy of the list of connections to avoid modification issues
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
        sessions_list.clear() # Beacons should be handled separately if they persist
        if not error:
            logger.info("All connections closed successfully")
            cprint("All connections closed", bg="green")
        else:
            logger.error("Not all connections could be closed")
            cprint("Not all connections could be closed", bg="red")
        return

    def close_from_multihandler(self) -> None:
        """
        Closes an individual client connection from the multi-handler.
        Args:
            None
        Returns:    
            None
        """

        logger.info("Closing individual client from multi handler")
        try:
            all_keys = list(sessions_list.keys()) + list(beacon_list.keys())
            if not all_keys:
                c_error("No connections to close.")
                return

            readline.set_completer(lambda text, state: tab_completion(text, state, all_keys))
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
                beacon.close_connection(uuid_to_close) # This should queue the command
                cprint(f"Beacon {uuid_to_close} will shutdown at next callback.", bg="green")
            else:
                cprint("Not a valid connection UUID.", bg="red")

        except (ValueError, IndexError) as e:
            logger.error(f"Error during close operation: {e}")
            cprint("An error occurred.", bg="red")
        return