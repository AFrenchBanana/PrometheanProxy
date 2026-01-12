"""
Interaction Handler Module - Modern UI with Styled Output

Handles interaction commands for sessions and beacons in the multi-handler module.
Provides clean terminal output using the UIManager pattern.
"""

import os
import readline
import ssl
import traceback
from typing import Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.table import Table
from rich.box import ROUNDED

from ...global_objects import sessions_list, tab_completion, beacon_list, logger
from ...utils.ui_manager import get_ui_manager
from ...beacon.beacon import add_beacon_command_list


class InteractionHandler:
    """
    Handles interaction commands for sessions and beacons in the multi-handler module.
    Uses modern UIManager for clean, styled terminal output.
    """

    def use_session(
        self, conn: ssl.SSLSocket, r_address: Tuple[str, int]
    ) -> None:
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

        ui.print_success(f"Interacting with session: {session_obj.hostname} ({r_address[0]})")
        logger.info(f"Starting session interaction with {session_obj.hostname}")

        # Build command handlers
        command_handlers = {
            "history": lambda: session_obj.history(r_address),
            "close": lambda: self._close_session(session_obj, session_id),
        }

        # Add dynamic session commands from plugins
        try:
            dynamic_commands = getattr(self, "list_loaded_session_commands", lambda: [])()
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
                command = self.prompt_session.prompt(
                    f"\n{r_address[0]} Session ❯ ",
                    completer=completer,
                ).lower().strip()
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
                    logger.error(f"Error executing '{command}': {e}\n{traceback.format_exc()}")
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

        ui.print_success(f"Interacting with beacon: {beacon_obj.hostname} ({beacon_obj.uuid[:12]}...)")
        logger.info(f"Beacon {beacon_obj.hostname} ({beacon_obj.uuid})