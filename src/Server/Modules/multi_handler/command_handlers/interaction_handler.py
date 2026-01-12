"""
Interaction Handler Module - Modern UI with Styled Output

Handles interaction commands for sessions and beacons in the multi-handler module.
Provides clean terminal output using the UIManager pattern.
"""

import readline
import ssl
import traceback
from typing import Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.box import ROUNDED
from rich.table import Table

from ...beacon.beacon import add_beacon_command_list
from ...global_objects import beacon_list, logger, sessions_list, tab_completion
from ...utils.ui_manager import get_ui_manager


class InteractionHandler:
    """
    Handles interaction commands for sessions and beacons in the multi-handler module.
    Uses modern UIManager for clean, styled terminal output.
    """

    def use_session(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """
        Interact with an individual session.

        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (ip, port)
        """
        ui = get_ui_manager()

        # Find session by address
        session_obj = None
        session_id = None
        for sid, sess in sessions_list.items():
            if sess.address == r_address or sess.details == conn:
                session_obj = sess
                session_id = sid
                break

        if not session_obj:
            logger.error(f"Session not found for address: {r_address}")
            ui.print_error(f"Session not found for {r_address[0]}:{r_address[1]}")
            return

        ui.print_success(
            f"Interacting with session: {session_obj.hostname} ({r_address[0]})"
        )
        logger.info(f"Starting session interaction with {session_obj.hostname}")

        # Build command handlers
        command_handlers = {
            "history": lambda: session_obj.history(r_address),
            "close": lambda: self._close_session(session_obj, session_id),
        }

        # Add dynamic session commands from plugins
        try:
            dynamic_commands = getattr(
                self, "list_loaded_session_commands", lambda: []
            )()
            for cmd in dynamic_commands or []:
                if cmd not in command_handlers:
                    command_handlers[cmd] = self._create_session_handler(
                        cmd, session_obj, conn, r_address, session_id
                    )
        except Exception as e:
            logger.debug(f"Error loading dynamic session commands: {e}")

        # Add module commands
        module_names = self._get_session_modules(session_obj)
        for mod in module_names:
            if mod not in command_handlers:
                command_handlers[mod] = self._create_session_module_handler(
                    mod, session_obj, conn, r_address, session_id
                )

        # Show available commands
        self._show_available_commands(command_handlers, "Session")

        # Create completer for prompt
        all_commands = list(command_handlers.keys()) + ["exit"]
        completer = WordCompleter(all_commands, ignore_case=True)

        # Main interaction loop
        while True:
            try:
                command = (
                    self.prompt_session.prompt(
                        f"\n{r_address[0]} Session ❯ ",
                        completer=completer,
                    )
                    .lower()
                    .strip()
                )
            except (EOFError, KeyboardInterrupt):
                break

            if command == "exit":
                ui.print_info("Exiting session interaction")
                break

            if not command:
                continue

            handler = command_handlers.get(command)
            if handler:
                try:
                    logger.info(f"Executing session command: {command}")
                    handler()
                    if command == "close":
                        break
                except Exception as e:
                    logger.error(
                        f"Error executing '{command}': {e}\n{traceback.format_exc()}"
                    )
                    ui.print_error(f"Command failed: {e}")
            else:
                ui.print_error(f"Unknown command: '{command}'")
                ui.print_info("Type 'exit' to return to main menu")

    def use_beacon(self, UserID: str, IPAddress: str) -> None:
        """
        Interact with an individual beacon.

        Args:
            UserID: UUID of the beacon
            IPAddress: IP address of the beacon
        """
        ui = get_ui_manager()
        logger.info(f"Using beacon with UserID: {UserID} and IPAddress: {IPAddress}")

        beacon_obj = beacon_list.get(UserID)
        if not beacon_obj:
            logger.error(f"No beacon found with UUID: {UserID}")
            ui.print_error(f"Beacon not found: {UserID}")
            return

        ui.print_success(
            f"Interacting with beacon: {beacon_obj.hostname} ({beacon_obj.uuid[:12]}...)"
        )
        logger.info(
            f"Beacon {beacon_obj.hostname} ({beacon_obj.uuid}) interaction started"
        )

        # Build command handlers for beacon
        command_handlers = {
            "history": lambda: beacon_obj.history(UserID),
            "list_commands": lambda: beacon_obj.list_db_commands(UserID),
            "config": lambda: beacon_obj.beacon_configuration(UserID),
            "switch_session": lambda: beacon_obj.switch_session(UserID),
            "close": lambda: beacon_obj.close_connection(UserID),
            "shell": lambda: self._beacon_shell_command(UserID, beacon_obj),
            "load_module": lambda: self._beacon_load_module(UserID, beacon_obj),
        }

        # Add dynamic beacon commands from plugins
        try:
            dynamic_commands = getattr(
                self, "list_loaded_beacon_commands", lambda: []
            )()
            for cmd in dynamic_commands or []:
                if cmd not in command_handlers:
                    command_handlers[cmd] = self._create_beacon_handler(
                        cmd, beacon_obj, UserID
                    )
        except Exception as e:
            logger.debug(f"Error loading dynamic beacon commands: {e}")

        # Add loaded module commands
        if hasattr(beacon_obj, "loaded_modules") and beacon_obj.loaded_modules:
            for mod in beacon_obj.loaded_modules:
                if mod not in command_handlers:
                    command_handlers[mod] = self._create_beacon_module_handler(
                        mod, beacon_obj, UserID
                    )

        # Show available commands
        self._show_available_commands(command_handlers, "Beacon")

        # Create completer for prompt
        all_commands = list(command_handlers.keys()) + ["exit", "help"]
        completer = WordCompleter(all_commands, ignore_case=True)

        # Main interaction loop
        while True:
            try:
                command = (
                    self.prompt_session.prompt(
                        f"\n{beacon_obj.hostname} Beacon ❯ ",
                        completer=completer,
                    )
                    .lower()
                    .strip()
                )
            except (EOFError, KeyboardInterrupt):
                ui.print_info("Exiting beacon interaction")
                break

            if command == "exit":
                ui.print_info("Exiting beacon interaction")
                break

            if command == "help":
                self._show_available_commands(command_handlers, "Beacon")
                continue

            if not command:
                continue

            handler = command_handlers.get(command)
            if handler:
                try:
                    logger.info(f"Executing beacon command: {command}")
                    handler()
                    if command == "close":
                        break
                except Exception as e:
                    logger.error(
                        f"Error executing '{command}': {e}\n{traceback.format_exc()}"
                    )
                    ui.print_error(f"Command failed: {e}")
            else:
                ui.print_error(f"Unknown command: '{command}'")
                ui.print_info(
                    "Type 'help' to see available commands or 'exit' to return"
                )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _show_available_commands(self, command_handlers: dict, context: str) -> None:
        """
        Display available commands in a styled table.

        Args:
            command_handlers: Dictionary of command name to handler function
            context: Context string (e.g., "Session" or "Beacon")
        """
        ui = get_ui_manager()

        table = Table(
            title=f"[bold bright_cyan]◆ Available {context} Commands[/]",
            box=ROUNDED,
            border_style="bright_cyan",
            header_style="bold bright_white on dark_cyan",
            padding=(0, 1),
            expand=False,
        )

        table.add_column("Command", style="bright_green")
        table.add_column("Description", style="white")

        # Command descriptions
        descriptions = {
            "history": "View command history",
            "list_commands": "List queued commands",
            "config": "Configure beacon parameters",
            "switch_session": "Switch beacon to session mode",
            "close": "Close the connection",
            "shell": "Execute shell command",
            "load_module": "Load a module on the beacon",
            "exit": "Return to main menu",
            "help": "Show this help message",
        }

        for cmd in sorted(command_handlers.keys()):
            desc = descriptions.get(cmd, f"Execute {cmd}")
            table.add_row(cmd, desc)

        table.add_row("[dim]exit[/]", "[dim]Return to main menu[/]")
        table.add_row("[dim]help[/]", "[dim]Show this help message[/]")

        ui.console.print(table)

    def _beacon_shell_command(self, user_id: str, beacon_obj) -> None:
        """
        Prompt for and queue a shell command for the beacon.

        Args:
            user_id: UUID of the beacon
            beacon_obj: Beacon object
        """
        ui = get_ui_manager()

        try:
            command = self.prompt_session.prompt("Enter shell command: ").strip()
            if not command:
                ui.print_warning("No command entered")
                return

            add_beacon_command_list(user_id, "shell", {"command": command})
            ui.print_success(f"Shell command queued: {command}")
            logger.info(f"Queued shell command for beacon {user_id}: {command}")
        except (EOFError, KeyboardInterrupt):
            ui.print_info("Cancelled")

    def _beacon_load_module(self, user_id: str, beacon_obj) -> None:
        """
        Prompt for and queue a module load command for the beacon.

        Args:
            user_id: UUID of the beacon
            beacon_obj: Beacon object
        """
        ui = get_ui_manager()

        try:
            # List available modules if the method exists
            if hasattr(self, "list_available_modules"):
                available = self.list_available_modules()
                if available:
                    ui.print_info(f"Available modules: {', '.join(available)}")

            module_name = self.prompt_session.prompt("Enter module name: ").strip()
            if not module_name:
                ui.print_warning("No module name entered")
                return

            # Use beacon's load_module method if available
            if hasattr(beacon_obj, "load_module"):
                beacon_obj.load_module(user_id, module_name)
            else:
                add_beacon_command_list(user_id, "module", {"name": module_name})

            ui.print_success(f"Module load queued: {module_name}")
            logger.info(f"Queued module load for beacon {user_id}: {module_name}")
        except (EOFError, KeyboardInterrupt):
            ui.print_info("Cancelled")

    def _create_beacon_handler(self, cmd: str, beacon_obj, user_id: str):
        """
        Create a handler function for a dynamic beacon command.

        Args:
            cmd: Command name
            beacon_obj: Beacon object
            user_id: UUID of the beacon

        Returns:
            Handler function
        """

        def handler():
            ui = get_ui_manager()
            try:
                # Try to get data for the command
                data = None
                if hasattr(self, "get_command_data"):
                    data = self.get_command_data(cmd)

                add_beacon_command_list(user_id, cmd, data)
                ui.print_success(f"Command '{cmd}' queued for beacon")
                logger.info(f"Queued command '{cmd}' for beacon {user_id}")
            except Exception as e:
                ui.print_error(f"Failed to queue command: {e}")
                logger.error(f"Error queuing command '{cmd}': {e}")

        return handler

    def _create_beacon_module_handler(self, module_name: str, beacon_obj, user_id: str):
        """
        Create a handler function for an already-loaded beacon module.

        Args:
            module_name: Name of the loaded module
            beacon_obj: Beacon object
            user_id: UUID of the beacon

        Returns:
            Handler function
        """

        def handler():
            ui = get_ui_manager()
            try:
                # Prompt for module arguments if needed
                args = self.prompt_session.prompt(
                    f"Enter arguments for {module_name} (or press Enter for none): "
                ).strip()

                data = {"name": module_name}
                if args:
                    data["args"] = args

                add_beacon_command_list(user_id, module_name, data)
                ui.print_success(f"Module '{module_name}' command queued")
                logger.info(
                    f"Queued module command '{module_name}' for beacon {user_id}"
                )
            except (EOFError, KeyboardInterrupt):
                ui.print_info("Cancelled")
            except Exception as e:
                ui.print_error(f"Failed to queue module command: {e}")
                logger.error(f"Error queuing module command '{module_name}': {e}")

        return handler

    def _close_session(self, session_obj, session_id: str) -> None:
        """
        Close a session connection.

        Args:
            session_obj: Session object
            session_id: UUID of the session
        """
        ui = get_ui_manager()
        try:
            session_obj.close_connection(session_obj.details, session_obj.address)
            ui.print_success(f"Session {session_id[:12]}... closed")
            logger.info(f"Closed session {session_id}")
        except Exception as e:
            ui.print_error(f"Failed to close session: {e}")
            logger.error(f"Error closing session {session_id}: {e}")

    def _create_session_handler(
        self, cmd: str, session_obj, conn, r_address, session_id: str
    ):
        """
        Create a handler function for a dynamic session command.

        Args:
            cmd: Command name
            session_obj: Session object
            conn: SSL socket connection
            r_address: Remote address tuple
            session_id: UUID of the session

        Returns:
            Handler function
        """

        def handler():
            ui = get_ui_manager()
            try:
                # Try to execute the command on the session
                if hasattr(session_obj, cmd):
                    method = getattr(session_obj, cmd)
                    method()
                elif hasattr(self, f"session_{cmd}"):
                    method = getattr(self, f"session_{cmd}")
                    method(session_obj, conn, r_address)
                else:
                    ui.print_error(f"Command '{cmd}' not implemented")
            except Exception as e:
                ui.print_error(f"Command failed: {e}")
                logger.error(f"Error executing session command '{cmd}': {e}")

        return handler

    def _create_session_module_handler(
        self, module_name: str, session_obj, conn, r_address, session_id: str
    ):
        """
        Create a handler function for a session module.

        Args:
            module_name: Name of the module
            session_obj: Session object
            conn: SSL socket connection
            r_address: Remote address tuple
            session_id: UUID of the session

        Returns:
            Handler function
        """

        def handler():
            ui = get_ui_manager()
            try:
                if hasattr(session_obj, "execute_module"):
                    session_obj.execute_module(module_name, conn, r_address)
                else:
                    ui.print_error("Module execution not supported for this session")
            except Exception as e:
                ui.print_error(f"Module execution failed: {e}")
                logger.error(f"Error executing module '{module_name}': {e}")

        return handler

    def _get_session_modules(self, session_obj) -> list:
        """
        Get list of available modules for a session.

        Args:
            session_obj: Session object

        Returns:
            List of module names
        """
        if hasattr(session_obj, "loaded_modules"):
            return session_obj.loaded_modules or []
        if hasattr(session_obj, "get_available_modules"):
            return session_obj.get_available_modules() or []
        return []
