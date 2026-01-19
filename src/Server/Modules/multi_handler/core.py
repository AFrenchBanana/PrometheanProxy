# ============================================================================
# Multi Handler Core Module
# ============================================================================
# This module contains the main MultiHandler class that manages multiple
# client sessions and beacon connections, providing a unified command
# interface for interacting with connected clients.
# ============================================================================

# Standard Library Imports
# Third-Party Imports
import threading
import time
import traceback

# Third-Party Imports
import colorama

# Local Imports
from Modules.beacon.beacon_server.websocket_server import publish_event
from Modules.multiplayer.multiplayer import MultiPlayer
from Modules.utils.config_configuration import beacon_config_menu, config_menu
from Modules.utils.console import colorize, success, warn
from Modules.utils.ui_manager import (
    get_ui_manager,
    log_connection_event,
    update_connection_stats,
)
from PacketSniffing.PacketSniffer import PacketSniffer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI
from ServerDatabase.database import DatabaseClass

from ..global_objects import (
    beacon_list,
    config,
    execute_local_commands,
    logger,
    sessions_list,
)
from .loader import LoaderMixin
from .multi_handler_commands import MultiHandlerCommands
from .security import SecurityMixin
from .socket_server import SocketServerMixin

# ============================================================================
# MultiHandler Class
# ============================================================================


class MultiHandler(SecurityMixin, SocketServerMixin, LoaderMixin):
    """
    Manages multiple client sessions and beacon connections.

    This class serves as the main controller for handling multiple simultaneous
    connections, including both interactive sessions and asynchronous beacons.
    It provides initialization, socket management, authentication, and command
    interface functionality.

    Inherits from:
        SecurityMixin: Provides certificate and HMAC creation methods
        SocketServerMixin: Provides socket server initialization and connection handling
        LoaderMixin: Provides database loading functionality

    Attributes:
        multihandlercommands: Command handler instance for user commands
        Authentication: Authentication handler for client verification
        database: Database instance for storing connection and command data
        isMultiplayer: Flag indicating if multiplayer mode is enabled
        multiplayer: MultiPlayer instance if multiplayer mode is active
        address: Tuple of (host, port) for the listening socket
    """

    def __init__(self) -> None:
        """Initialize the MultiHandler with all necessary components."""
        from Modules import global_objects

        from ..utils.authentication import Authentication

        logger.info("Starting MultiHandler")

        # Initialize UI Manager
        self.ui_manager = get_ui_manager()
        self.prompt_session = PromptSession()

        # Initialize core components
        self.multihandlercommands = MultiHandlerCommands(config, self.prompt_session)
        self.Authentication = Authentication()
        # Use shared database instance to avoid multiple initializations
        self.database = global_objects.get_database("command_database")

        # Set up security certificates and keys
        self.create_certificate()
        self.create_hmac()

        # Load existing implants from database
        self.load_db_implants()

        # Initialize colorama for colored terminal output
        colorama.init(autoreset=True)

        # Initialize packet sniffer if enabled in config
        if config["packetsniffer"]["active"]:
            sniffer = PacketSniffer()
            sniffer.start_raw_socket()
            logger.info("PacketSniffer started")
            log_connection_event("info", "PacketSniffer started")

        # Initialize multiplayer mode if enabled
        self.isMultiplayer = False
        try:
            if config["multiplayer"]["multiplayerEnabled"]:
                self.isMultiplayer = True
                self.multiplayer = MultiPlayer(config)
                self.multihandlercommands = MultiHandlerCommands(
                    config, self.prompt_session
                )
                success("Multiplayer mode enabled")
                logger.info("Server: Multiplayer mode enabled")
                log_connection_event("info", "Multiplayer mode enabled")
                threading.Thread(target=self.multiplayer.start, daemon=True).start()
        except KeyError as e:
            warn("Multiplayer configuration not found, continuing in singleplayer mode")
            traceback.print_exc()
            warn(str(e))
            logger.info("Server: Continuing in singleplayer mode")

        # Start late beacon checker
        threading.Thread(target=self.check_late_beacons, daemon=True).start()

    def check_late_beacons(self):
        """Periodically checks for and reports late beacons."""
        while True:
            time.sleep(60)  # Check every 60 seconds
            current_time = time.time()
            for beacon in beacon_list.values():
                try:
                    next_beacon_time = time.mktime(
                        time.strptime(beacon.next_beacon, "%a %b %d %H:%M:%S %Y")
                    )
                    if current_time > next_beacon_time and not beacon.is_late:
                        beacon.is_late = True
                        event_data = {
                            "type": "live_event",
                            "event": "late_checkin",
                            "hostname": beacon.hostname,
                            "uuid": beacon.uuid,
                            "last_seen": beacon.last_beacon,
                            "next_beacon": beacon.next_beacon,
                        }
                        publish_event(event_data)
                        logger.warning(
                            f"Beacon {beacon.hostname} ({beacon.uuid}) is late. Last seen: {beacon.last_beacon}"
                        )
                except Exception as e:
                    logger.error(f"Error checking late beacon {beacon.uuid}: {e}")

    # ========================================================================
    # Command Interface Methods
    # ========================================================================

    def multi_handler(self, config: dict) -> None:
        """
        Main command interface loop for user interaction.

        Provides an interactive command prompt where operators can manage
        sessions, beacons, and server configuration. Handles command routing
        and execution with a modern terminal UI.

        Args:
            config: Configuration dictionary containing server settings
        """
        logger.info("Starting MultiHandler menu")

        # Update initial stats
        update_connection_stats(len(sessions_list), len(beacon_list))

        # Log initial server start
        log_connection_event(
            "info", f"Server started on {self.address[0]}:{self.address[1]}"
        )
        log_connection_event(
            "info", f"Beacon server on port {config['server']['webPort']}"
        )

        # Configure tab completion
        available_commands = [
            "list",
            "sessions",
            "beacons",
            "close",
            "closeall",
            "users" if self.isMultiplayer else None,
            "configbeacon",
            "command",
            "hashfiles",
            "config",
            "configBeacon",
            "logs",
            "plugins",
            "help",
            "status",
            "clear",
            "exit",
        ]
        available_commands = [cmd for cmd in available_commands if cmd is not None]
        completer = WordCompleter(available_commands, ignore_case=True)

        # Print startup messages
        self.ui_manager.print_success(
            f"Server listening on [bright_cyan]{self.address[0]}:{self.address[1]}[/]"
        )
        self.ui_manager.print_success(
            f"Beacon server on port [bright_cyan]{config['server']['webPort']}[/]"
        )

        if config["packetsniffer"]["active"]:
            self.ui_manager.print_success(
                f"PacketSniffing active on port [bright_cyan]{config['packetsniffer']['port']}[/]"
            )
            logger.info("PacketSniffing is active")
            log_connection_event(
                "info", f"PacketSniffer on port {config['packetsniffer']['port']}"
            )

        self.ui_manager.print("")
        self.ui_manager.print(
            "[dim]Type [bright_magenta]help[/] for available commands, "
            "[bright_cyan]TAB[/] for completion[/]"
        )
        self.ui_manager.print("")

        # --------------------------------------------------------
        # Command Handler Functions
        # --------------------------------------------------------
        def handle_sessions():
            """Route to session selection interface."""
            logger.debug("Handling sessions command")
            if len(sessions_list) == 0:
                self.ui_manager.print_error("No sessions connected")
            else:
                self.multihandlercommands.sessionconnect()

        def handle_beacons():
            """Route to beacon selection interface."""
            logger.debug("Handling beacons command")
            if len(beacon_list) == 0:
                self.ui_manager.print_error("No beacons connected")
                logger.warning("No beacons connected")
            elif len(beacon_list) > 1:
                # Show beacon list first
                self.ui_manager.console.print(
                    self.ui_manager.create_beacons_table(beacon_list)
                )
                try:
                    index = int(self.prompt_session.prompt("Enter beacon index: "))
                except ValueError:
                    self.ui_manager.print_error("Invalid index input")
                    logger.error("Invalid index input for beacon selection")
                    return
                logger.debug(f"Selected beacon index: {index}")
                try:
                    beacon = list(beacon_list.values())[index]
                    self.multihandlercommands.use_beacon(beacon.uuid, beacon.address)
                    logger.info(f"Using beacon {beacon.uuid} at {beacon.address}")
                except IndexError:
                    self.ui_manager.print_error("Index out of range")
                    logger.error("Index out of range for beacon selection")
            else:
                beacon = list(beacon_list.values())[0]
                self.multihandlercommands.use_beacon(beacon.uuid, beacon.address)

        def handle_status():
            """Display current status."""
            self.ui_manager.update_stats(len(sessions_list), len(beacon_list))
            self.ui_manager.console.print(self.ui_manager.create_status_table())

        def handle_help():
            """Display help information."""
            help_commands = {
                "list": "List all active connections",
                "sessions": "Interact with active sessions",
                "beacons": "Interact with active beacons",
                "close": "Close a specific connection",
                "closeall": "Close all connections",
                "config": "Server configuration menu",
                "configbeacon": "Beacon configuration menu",
                "hashfiles": "Hash local database files",
                "logs": "View server logs",
                "plugins": "List available plugins",
                "status": "Show connection status",
                "clear": "Clear terminal screen",
                "exit": "Exit the server",
            }
            if self.isMultiplayer:
                help_commands["users"] = "Multiplayer user menu"
            self.ui_manager.console.print(
                self.ui_manager.create_help_table(help_commands)
            )

        def handle_clear():
            """Clear the terminal output."""
            self.ui_manager.console.clear()
            self.ui_manager.print_info("Terminal cleared")

        # Command routing dictionary
        command_handlers = {
            "list": self.multihandlercommands.listconnections,
            "sessions": handle_sessions,
            "beacons": handle_beacons,
            "close": lambda: self.multihandlercommands.close_from_multihandler(),
            "closeall": lambda: self.multihandlercommands.close_all_connections(),
            "hashfiles": self.multihandlercommands.localDatabaseHash,
            "config": config_menu,
            "configbeacon": beacon_config_menu,
            "users": (
                self.multiplayer.userMenu
                if self.isMultiplayer
                else (
                    lambda: self.ui_manager.print_error(
                        "Multiplayer mode is not enabled"
                    )
                )
            ),
            "logs": self.multihandlercommands.view_logs,
            "plugins": self.multihandlercommands.plugins,
            "clear": handle_clear,
            "status": handle_status,
            "help": handle_help,
        }

        # Main command loop
        try:
            while True:
                # Get user command with styled prompt
                try:
                    command = (
                        self.prompt_session.prompt(
                            ANSI(
                                colorize(
                                    "\nMultiHandler ❯ ",
                                    fg="bright_magenta",
                                    bold=True,
                                )
                            ),
                            completer=completer,
                        )
                        .lower()
                        .strip()
                    )
                except EOFError:
                    self.ui_manager.print_error("Use 'exit' command to quit")
                    continue
                except KeyboardInterrupt:
                    self.ui_manager.print_warning("Use 'exit' command to quit properly")
                    continue

                if not command:
                    continue

                logger.debug(f"Received command: {command}")

                # Exit command - shutdown server
                if command == "exit":
                    self.ui_manager.print_warning(
                        "Closing connections and shutting down..."
                    )
                    log_connection_event("info", "Server shutting down")
                    break

                # Execute command
                try:
                    logger.debug(f"Executing command: {command}")
                    handler = command_handlers.get(command)
                    if handler:
                        handler()
                    else:
                        logger.debug(f"Unknown command, trying local: {command}")
                        if not execute_local_commands(command):
                            self.ui_manager.print_error(f"Unknown command: '{command}'")
                            self.ui_manager.print_info(
                                "Type 'help' for available commands"
                            )
                except Exception as e:
                    self.ui_manager.print_error(f"Error: {str(e)}")
                    logger.error(f"Command error: {e}")
                    if not config["server"]["quiet_mode"]:
                        traceback.print_exc()

        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt received, exiting MultiHandler")
            self.ui_manager.print_warning("Interrupted - shutting down")
