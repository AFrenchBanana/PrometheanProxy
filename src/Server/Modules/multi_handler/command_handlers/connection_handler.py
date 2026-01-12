# ============================================================================
# Connection Handler Module
# ============================================================================
# This module provides connection management commands for the multi-handler,
# including listing connections, connecting to sessions, and closing connections.
# ============================================================================

# Standard Library Imports
import readline
import time

# Third-Party Imports
from rich.table import Table
from rich.box import ROUNDED, MINIMAL_DOUBLE_HEAD

from ...beacon.beacon import remove_beacon_list
from ...global_objects import (
    beacon_list,
    logger,
    multiplayer_connections,
    sessions_list,
    tab_completion,
)
from ...session.session import remove_connection_list
from ...utils.ui_manager import get_ui_manager

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

    def listconnections(self) -> None:
        """
        List all active connections including sessions and beacons.

        Displays formatted tables showing details of active sessions, beacons,
        and multiplayer connections (if enabled). Includes timing information
        for beacons and status indicators.
        """
        ui = get_ui_manager()

        # ----------------------------------------------------------------
        # Display Active Sessions
        # ----------------------------------------------------------------
        logger.info("Listing all active connections")

        if len(sessions_list) == 0:
            ui.print_warning("No active sessions")
        else:
            logger.info("Creating sessions table")

            session_table = Table(
                title="[bold bright_green]● Active Sessions[/]",
                box=ROUNDED,
                border_style="bright_green",
                header_style="bold bright_white on dark_green",
                row_styles=["", "dim"],
                padding=(0, 1),
                expand=True,
            )

            session_table.add_column("#", style="dim", width=4, justify="right")
            session_table.add_column("UUID", style="bright_blue", max_width=14, no_wrap=True)
            session_table.add_column("Hostname", style="bright_green")
            session_table.add_column("IP Address", style="white")
            session_table.add_column("OS", style="bright_cyan")
            session_table.add_column("Mode", style="bright_magenta")

            for idx, (userID, session) in enumerate(sessions_list.items()):
                uuid_display = str(userID)[:12] + "..." if len(str(userID)) > 12 else str(userID)
                addr_display = session.address[0] if isinstance(session.address, tuple) else str(session.address)

                session_table.add_row(
                    str(idx),
                    uuid_display,
                    str(session.hostname),
                    addr_display,
                    str(session.operating_system),
                    str(getattr(session, 'mode', 'session')),
                )

            logger.info("Printing sessions table")
            ui.console.print(session_table)

        # ----------------------------------------------------------------
        # Display Active Beacons
        # ----------------------------------------------------------------
        ui.print("")  # Spacer

        if len(beacon_list) == 0:
            logger.info("No active beacons found")
            ui.print_warning("No active beacons")
        else:
            beacon_table = Table(
                title="[bold bright_cyan]◆ Active Beacons[/]",
                box=ROUNDED,
                border_style="bright_cyan",
                header_style="bold bright_white on dark_cyan",
                row_styles=["", "dim"],
                padding=(0, 1),
                expand=True,
            )

            beacon_table.add_column("#", style="dim", width=4, justify="right")
            beacon_table.add_column("UUID", style="bright_blue", max_width=14, no_wrap=True)
            beacon_table.add_column("Hostname", style="bright_cyan")
            beacon_table.add_column("IP", style="white")
            beacon_table.add_column("OS", style="bright_magenta")
            beacon_table.add_column("Last Seen", style="bright_yellow", max_width=20)
            beacon_table.add_column("Status", style="white", max_width=30)

            for idx, (userID, beacon) in enumerate(beacon_list.items()):
                uuid_display = str(userID)[:12] + "..." if len(str(userID)) > 12 else str(userID)

                # Calculate beacon status
                status_text = ""
                row_style = ""

                try:
                    next_beacon_time = time.strptime(
                        beacon.next_beacon, "%a %b %d %H:%M:%S %Y"
                    )
                    current_time = time.strptime(time.asctime(), "%a %b %d %H:%M:%S %Y")

                    if time.mktime(current_time) > time.mktime(next_beacon_time):
                        # Beacon is late
                        time_diff = time.mktime(current_time) - time.mktime(next_beacon_time)
                        if time_diff < beacon.jitter:
                            status_text = f"[bright_yellow]◐ Late ({int(time_diff)}s, within jitter)[/]"
                        else:
                            status_text = f"[bright_red]○ Late ({int(time_diff)}s)[/]"
                    else:
                        # Beacon is on time
                        time_until = int(time.mktime(next_beacon_time) - time.mktime(current_time))
                        status_text = f"[bright_green]● Active (next: {time_until}s)[/]"
                except (ValueError, TypeError, AttributeError):
                    status_text = "[dim]◐ Awaiting check-in[/]"

                # Mark beacons loaded from database
                if hasattr(beacon, 'loaded_this_instant') and not beacon.loaded_this_instant:
                    status_text = "[bright_yellow]◇ Loaded from DB[/]"

                beacon_table.add_row(
                    str(idx),
                    uuid_display,
                    str(beacon.hostname),
                    str(beacon.address),
                    str(beacon.operating_system),
                    str(beacon.last_beacon) if hasattr(beacon, 'last_beacon') else "N/A",
                    status_text,
                )

            ui.console.print(beacon_table)

        # ----------------------------------------------------------------
        # Display Multiplayer Connections (if enabled)
        # ----------------------------------------------------------------
        try:
            multiplayer_enabled = self.config["multiplayer"]["multiplayerEnabled"]
        except KeyError:
            multiplayer_enabled = False

        if multiplayer_enabled:
            ui.print("")  # Spacer

            if not multiplayer_connections:
                ui.print_warning("No active multiplayer connections")
            else:
                mp_table = Table(
                    title="[bold bright_magenta]◈ Multiplayer Connections[/]",
                    box=ROUNDED,
                    border_style="bright_magenta",
                    header_style="bold bright_white on purple4",
                    padding=(0, 1),
                    expand=True,
                )

                mp_table.add_column("Username", style="bright_cyan")
                mp_table.add_column("Address", style="white")

                for username, client in multiplayer_connections.items():
                    try:
                        addr = (
                            client.address[0]
                            if isinstance(client.address, (list, tuple))
                            else str(client.address)
                        )
                    except Exception:
                        addr = "unknown"
                    mp_table.add_row(username, addr)

                ui.console.print(mp_table)

    # ========================================================================
    # Session Connection Methods
    # ========================================================================

    def sessionconnect(self) -> None:
        """
        Connect to a session from the list of active sessions.
        Prompts the user to select a session (if multiple exist) and
        establishes an interactive session with the selected client.
        """
        ui = get_ui_manager()

        try:
            keys = list(sessions_list.keys())
            if not keys:
                ui.print_error("No active sessions to connect to.")
                return

            if len(sessions_list) == 1:
                logger.info("Only one session available, connecting to it")
                session_id = keys[0]
            else:
                logger.info("Multiple sessions available, prompting user for selection")

                # Show session list
                ui.console.print(ui.create_sessions_table(sessions_list))

                try:
                    index = int(self.prompt_session.prompt("Enter session index: "))
                    if index < 0 or index >= len(keys):
                        ui.print_error("Index out of range")
                        return
                    session_id = keys[index]
                except ValueError:
                    ui.print_error("Invalid input. Please enter a number.")
                    return

            session = sessions_list.get(session_id)
            if session:
                ui.print_success(f"Connecting to session: {session.hostname}")
                self.use_session(session.details, session.address)
            else:
                ui.print_error(f"Session {session_id} not found")

        except Exception as e:
            logger.error(f"Error connecting to session: {e}")
            ui.print_error(f"An error occurred: {e}")

    # ========================================================================
    # Connection Closing Methods
    # ========================================================================

    def close_from_multihandler(self) -> None:
        """
        Close an individual connection (session or beacon) from the multi-handler.
        Prompts for the UUID of the connection to close.
        """
        ui = get_ui_manager()

        logger.info("Closing individual client from multi handler")
        try:
            all_keys = list(sessions_list.keys()) + list(beacon_list.keys())
            if not all_keys:
                ui.print_warning("No connections to close.")
                return

            readline.set_completer(
                lambda text, state: tab_completion(text, state, all_keys)
            )

            # Show current connections first
            self.listconnections()

            uuid_to_close = self.prompt_session.prompt(
                "\nEnter UUID to close: "
            ).strip()

            logger.info(f"User wants to close client with UUID: {uuid_to_close}")

            if uuid_to_close in sessions_list:
                session = sessions_list[uuid_to_close]
                session.close_connection(session.details, session.address)
                ui.print_success(f"Session {uuid_to_close[:12]}... closed")

            elif uuid_to_close in beacon_list:
                logger.info(f"Queueing close command for beacon with ID: {uuid_to_close}")
                beacon = beacon_list[uuid_to_close]
                beacon.close_connection(uuid_to_close)
                ui.print_success(f"Beacon {uuid_to_close[:12]}... will shutdown at next callback")

            else:
                ui.print_error("Not a valid connection UUID")

        except (ValueError, IndexError) as e:
            logger.error(f"Error during close operation: {e}")
            ui.print_error("An error occurred")

    def close_all_connections(self) -> None:
        """
        Close all active connections (both sessions and beacons).
        Prompts for confirmation before closing.
        """
        ui = get_ui_manager()

        logger.info("Closing all connections")

        total = len(sessions_list) + len(beacon_list)
        if total == 0:
            ui.print_warning("No connections to close")
            return

        # Confirm action
        confirm = self.prompt_session.prompt(
            f"Close all {total} connection(s)? [y/N]: "
        ).strip().lower()

        if confirm != 'y':
            ui.print_info("Cancelled")
            return

        # Close all sessions
        closed_sessions = 0
        for session_id in list(sessions_list.keys()):
            try:
                session = sessions_list[session_id]
                session.close_connection(session.details, session.address)
                closed_sessions += 1
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")

        # Queue close commands for all beacons
        closed_beacons = 0
        for beacon_id in list(beacon_list.keys()):
            try:
                beacon = beacon_list[beacon_id]
                beacon.close_connection(beacon_id)
                closed_beacons += 1
            except Exception as e:
                logger.error(f"Error closing beacon {beacon_id}: {e}")

        ui.print_success(f"Closed {closed_sessions} session(s), queued shutdown for {closed_beacons} beacon(s)")
