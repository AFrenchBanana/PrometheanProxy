from ...beacon.beacon import add_beacon_command_list
from ...global_objects import (
    sessions_list,
    tab_completion,
    beacon_list,
    logger
)
from ...utils.console import cprint, warn, error as c_error

from typing import Tuple
import colorama
import readline
import ssl
import traceback
import os


class InteractionHandler:
    """
    Handles interaction commands for sessions and beacons in the multi-handler module.
    Args:
        None
    Returns:
        None
    """

    def current_client_session(self, conn: ssl.SSLSocket,
                               r_address: Tuple[str, int], user_ID) -> None:
        """"
        Function that interacts with an individual session,
        passing connection details through to the current_client function.
        Args:
            conn (ssl.SSLSocket): The SSL socket connection to the client
            r_address (Tuple[str, int]): The remote address of the client
            user_ID: The unique identifier for the session
        Returns:
            None
        """
        session_obj = sessions_list.get(user_ID)
        if not session_obj:
            logger.error(f"Session not found for user ID: {user_ID}")
            return

        # Only dynamic plugin commands for sessions
        command_handlers = {}
        try:
            dynamic_commands = getattr(self, "list_loaded_session_commands")()
        except Exception:
            dynamic_commands = []

        # Prefer a module-aware wrapper for dynamic session commands as well,
        # so even if on-disk discovery fails we still check/load before running.
        for cmd in dynamic_commands or []:
            def _session_dyn_handler(mod=cmd):
                """
                 Handles dynamic session commands with module loading checks.
                Args:
                    mod: The module name for the command
                Returns:
                    None"""

                def _inner():

                    """
                    Executes the session plugin command after ensuring the module is loaded.
                    Args:
                        None
                    Returns:
                        None
                    """
                    try:
                        # If the module is already loaded, just refresh plugins and run.
                        if hasattr(session_obj, 'loaded_modules') and mod in getattr(session_obj, 'loaded_modules', set()):
                            try:
                                getattr(self, "load_plugins")()
                            except Exception:
                                pass
                            return self.run_session_plugin(mod, conn, r_address, user_ID)

                        # Otherwise ask to load the module first.
                        choice = input(f"Module '{mod}' is not loaded. Load now? [y/N]: ").strip().lower()
                        if choice.startswith('y'):
                            session_obj.load_module_direct_session(conn, r_address, mod)
                            try:
                                getattr(self, "load_plugins")()
                            except Exception:
                                pass
                            return self.run_session_plugin(mod, conn, r_address, user_ID)
                        else:
                            warn("Cancelled.")
                    except Exception as e:
                        logger.error(f"Failed to handle session plugin '{mod}': {e}")
                        c_error(f"An error occurred: {e}")
                return _inner
            command_handlers[cmd] = _session_dyn_handler()

        # Add dynamic commands for predefined client modules
        try:
            platform_folder = 'windows' if 'windows' in session_obj.operating_system else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            channel = 'debug' if 'debug' in session_obj.operating_system else 'release'
            module_base = os.path.expanduser(session_obj.config['server']['module_location'])
            module_dir = os.path.abspath(os.path.join(module_base, platform_folder, channel))
            files = [f for f in os.listdir(module_dir) if f.endswith(ext)]
            module_names = [os.path.splitext(f)[0] for f in files]
        except Exception:
            module_names = []

        # Wire up discovered on-disk modules (if any). Always use a module-aware handler
        # so we prompt to load if missing before running the session plugin.
        for m in module_names:
            def _session_module_handler(mod=m):
                def _inner():
                    if mod in session_obj.loaded_modules:
                        try:
                            getattr(self, "load_plugins")()
                            self.run_session_plugin(mod, conn, r_address, user_ID)
                            cprint(f"Ran session plugin '{mod}'.", fg="green")
                        except Exception as e:
                            logger.error(f"Failed to run session plugin '{mod}' after detecting loaded module: {e}")
                        return
                    # Ask to load the module, then run the plugin command
                    choice = input(f"Module '{mod}' is not loaded. Load now? [y/N]: ").strip().lower()
                    if choice.startswith('y'):
                        session_obj.load_module_direct_session(conn, r_address, mod)
                        try:
                            getattr(self, "load_plugins")()
                            self.run_session_plugin(mod, conn, r_address, user_ID)
                            cprint(f"Ran session plugin '{mod}' after loading module.", fg="green")
                        except Exception as e:
                            logger.error(f"Failed to run session plugin '{mod}' after loading module: {e}")
                    else:
                        warn("Cancelled.")
                return _inner
            command_handlers[m] = _session_module_handler()

        # Optional: show available commands once when entering the session menu
        if command_handlers:
            cprint("Available commands: " + ", ".join(sorted(command_handlers.keys()) + ["exit"]), fg="yellow")

        while True:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(text, state, list(command_handlers.keys()) + ["exit"]))

            command = input(f"{r_address[0]}:{r_address[1]} Command: ").lower().strip()

            logger.info(f"Command input is {command}")
            if command == "exit":
                break

            handler = command_handlers.get(command)
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Error executing command '{command}': {e}\n{traceback.format_exc()}")
                    c_error(f"An error occurred: {e}")
            else:
                if command != "":
                    c_error(f"Unknown command: '{command}'")
        return

    def use_beacon(self, UserID, IPAddress) -> None:
        """
        Function that interacts with an individual beacon,
        passing connection details through to the use_beacon function.
        Args:
            UserID: The unique identifier for the beacon
            IPAddress: The IP address of the beacon
        Returns:
            None
        """
        
        logger.info(f"Using beacon with UserID: {UserID} and IPAddress: {IPAddress}")
        beaconClass = beacon_list.get(UserID)
        if not beaconClass:
            logger.error(f"No beacon found with UUID: {UserID}")
            print(f"No beacon found with UUID: {UserID}")
            return
        
        cprint(f"Interacting with beacon {beaconClass.hostname} ({beaconClass.uuid})", fg="yellow")
        logger.info(f"Beacon {beaconClass.hostname} ({beaconClass.uuid}) found")

        def get_command_handlers():
            # Only static; all other commands are plugins
            command_handlers = {
                "close": lambda: beaconClass.close_connection(UserID),
                "module": lambda: beaconClass.load_module_beacon(UserID),
                "session": lambda: beaconClass.switch_session(UserID)
            }

            # Merge in dynamic beacon plugins via MultiHandlerCommands
            try:
                dynamic_beacon = getattr(self, "list_loaded_beacon_commands")()
            except Exception:
                dynamic_beacon = []

            for cmd in dynamic_beacon or []:
                if cmd not in command_handlers:
                    # Wrap dynamic beacon commands with a module-aware handler so we prompt
                    # to load missing modules before attempting to run the plugin.
                    def _beacon_dyn_handler(mod=cmd):
                        def _inner():
                            try:
                                if hasattr(beaconClass, 'loaded_modules') and mod in getattr(beaconClass, 'loaded_modules', set()):
                                    try:
                                        getattr(self, "load_plugins")()
                                    except Exception:
                                        pass
                                    if self.run_beacon_plugin(mod, UserID):
                                        cprint(f"Queued beacon plugin '{mod}' for {UserID}.", fg="green")
                                    return

                                choice = input(f"Module '{mod}' is not loaded. Load now? [y/N]: ").strip().lower()
                                if choice.startswith('y'):
                                    beaconClass.load_module_direct_beacon(UserID, mod)
                                    try:
                                        getattr(self, "load_plugins")()
                                    except Exception:
                                        pass
                                    if self.run_beacon_plugin(mod, UserID):
                                        cprint(f"Queued beacon plugin {mod} for {UserID} after loading module.", fg="green")
                                else:
                                    warn("Cancelled.")
                            except Exception as e:
                                logger.error(f"Failed to handle beacon plugin '{mod}': {e}")
                                if not self.config['server']['quiet_mode']:
                                    c_error(f"An error occurred: {e}")
                        return _inner
                    command_handlers[cmd] = _beacon_dyn_handler()

            # Discover on-disk modules and wire commands
            def _resolve_module_base() -> str:
                """
                Resolves the base directory for modules, preferring unified structure.
                Returns:
                    str: Path to the module base directory  
                """
                candidates = [
                    os.path.expanduser(beaconClass.config['server'].get('module_location', '')),
                    os.path.expanduser('~/.PrometheanProxy/plugins'),
                ]
                for c in candidates:
                    if c and os.path.isdir(c):
                        return c
                return os.path.expanduser('~/.PrometheanProxy/plugins')

            command_location = _resolve_module_base()
            repo_plugins = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Plugins")) 
            try:
                os_str = str(beaconClass.operating_system).lower()
                platform_folder = 'windows' if 'windows' in os_str else 'linux'
                ext = '.dll' if platform_folder == 'windows' else '.so'
                channel = 'debug' if 'debug' in os_str else 'release'
                module_names = []

                # Legacy structure has OS folders at root (linux/windows/<channel>/*.ext)
                legacy_linux = os.path.join(command_location, 'linux')
                legacy_windows = os.path.join(command_location, 'windows')
                if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                    files = []
                    for ch in ('release', 'debug'):
                        d = os.path.join(command_location, platform_folder, ch)
                        if os.path.isdir(d):
                            files.extend([f for f in os.listdir(d) if f.endswith(ext)])
                    module_names = [os.path.splitext(f)[0].removesuffix('-debug') for f in files]
                else:
                    # Unified structure: <name>/{release,debug}/{name}[ -debug].ext
                    if os.path.isdir(command_location):
                        for name in os.listdir(command_location):
                            full = os.path.join(command_location, name)
                            if not os.path.isdir(full):
                                continue
                            fname = f"{name}{'-debug' if channel == 'debug' else ''}{ext}"
                            cand = os.path.join(full, channel, fname)
                            if os.path.isfile(cand):
                                module_names.append(name)

                    # Fallback to repo tree if none found in user directory
                    if not module_names and os.path.isdir(repo_plugins):
                        for name in os.listdir(repo_plugins):
                            full = os.path.join(repo_plugins, name)
                            if not os.path.isdir(full):
                                continue
                            fname = f"{name}{'-debug' if channel == 'debug' else ''}{ext}"
                            cand = os.path.join(full, channel, fname)
                            if os.path.isfile(cand):
                                module_names.append(name)

            except Exception as e:
                logger.error(f"Error listing modules: {e}")
                module_names = []

            for m in module_names:
                # Always override with a module-aware handler so we can prompt to load if needed
                def _beacon_module_handler(mod=m):
                    def _inner():
                        if mod in beaconClass.loaded_modules:
                            # Ensure plugins are discovered, then run the plugin command
                            try:
                                getattr(self, "load_plugins")()
                                if self.run_beacon_plugin(mod, UserID):
                                    cprint(f"Queued beacon plugin '{mod}' for {UserID}.", fg="green")
                                    return
                            except Exception as e:
                                logger.error(f"Failed to run beacon plugin '{mod}' after detecting loaded module: {e}")
                            
                            # Fallback if no plugin handled it
                            add_beacon_command_list(UserID, None, mod, {})
                            cprint(f"Queued command '{mod}' for {UserID}.", fg="green")
                            return
                        
                        # Ask to load the module, then run the plugin command
                        choice = input(f"Module '{mod}' is not loaded. Load now? [y/N]: ").strip().lower()
                        if choice.startswith('y'):
                            beaconClass.load_module_direct_beacon(UserID, mod)
                            try:
                                getattr(self, "load_plugins")()
                                if self.run_beacon_plugin(mod, UserID):
                                    cprint(f"Queued beacon plugin {mod} for {UserID} after loading module.", fg="green")
                            except Exception as e:
                                logger.error(f"Failed to run beacon plugin '{mod}' after loading module: {e}")
                        else:
                            warn("Cancelled.")
                    return _inner
                if m not in command_handlers:
                    command_handlers[m] = _beacon_module_handler()
            
            return command_handlers

        command_handlers = get_command_handlers() # Initial load

        # Optional: show available commands once when entering the beacon menu
        if command_handlers:
            cprint("Available commands: " + ", ".join(sorted(command_handlers.keys()) + ["exit"]), fg="yellow")

        while True:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(text, state, list(command_handlers.keys()) + ["exit"]))

            command = input(f"{UserID} Command: ").lower().strip()

            logger.info(f"Command input is {command}")
            if command == "exit":
                break

            handler = command_handlers.get(command)
            if handler:
                try:
                    logger.info(f"Executing/queueing command: {command}")
                    handler()
                    logger.info(f"Executed/queued command: {command}")
                    if command == "close":
                        return
                except Exception as e:
                    logger.error(f"Error with command '{command}': {e}\n{traceback.format_exc()}")
                    if not self.config['server']['quiet_mode']:
                        c_error("Traceback:")
                        traceback.print_exc()
            else:
                c_error(f"Unknown command: '{command}'")
        return