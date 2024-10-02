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
    sessions,
    send_data,
    receive_data,
    config,
    tab_completion,
    beacons,
    beacon_commands,
    remove_beacon_list,
    add_beacon_command_list
)

from typing import Tuple

import hashlib
import os
import tqdm
import colorama
import socket
import readline
import ssl
import time
import uuid


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
                               r_address: Tuple[str, int], uuid) -> None:
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
        while True:
            # resets colorama after each statement
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state:
                    tab_completion(text, state, [
                        "shell", "close", "processes", "sysinfo", "checkfiles",
                        "download", "upload", "services", "netstat",
                        "diskusage", "listdir, beacon"
                    ]))
            command = (input(colorama.Fore.YELLOW +
                             f"{r_address[0]}:{r_address[1]} Command: ")
                       .lower())
            if command == "exit":  # exits back to multihandler menu
                break
            try:  # calls command
                if command == "shell":
                    self.sessioncommands.shell(conn, r_address)
                elif command == "close":
                    self.sessioncommands.close_connection(conn, r_address)
                    return
                elif command == "processes":
                    self.sessioncommands.list_processes(conn, r_address)
                elif command == "sysinfo":
                    self.sessioncommands.systeminfo(conn, r_address)
                elif command == "checkfiles":
                    self.sessioncommands.checkfiles(conn)
                elif command == "download":
                    self.sessioncommands.DownloadFiles(conn)
                elif command == "upload":
                    self.sessioncommands.UploadFiles(conn)
                elif command == "services":
                    self.sessioncommands.list_services(conn, r_address)
                elif command == "netstat":
                    self.sessioncommands.netstat(conn, r_address)
                elif command == "diskusage":
                    self.sessioncommands.diskusage(conn, r_address)
                elif command == "listdir":
                    self.sessioncommands.list_dir(conn, r_address)
                elif command == "beacon":
                    for i, details in enumerate(sessions["details"]):
                        if details == conn:
                            if sessions["uuid"][i] == uuid:
                                self.sessioncommands.change_beacon(
                                    conn, r_address, sessions["uuid"][i])
                        return
                elif not exec(command):
                    print((colorama.Fore.GREEN +
                           config['SessionModules']['help']))
            except (KeyError, SyntaxError, AttributeError) as e:
                # if the command is not matched then it prints help menu
                print((colorama.Fore.GREEN + config['SessionModules']['help']) + str(e) + "Error HERE")
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
        'netstat', 'diskusage', 'listdir'])
        """
        while True:
            # resets colorama after each statement
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state:
                    tab_completion(text, state, [
                        "shell", "close", "processes", "sysinfo", "checkfiles",
                        "download", "upload", "services", "netstat",
                        "diskusage", "listdir, beacon"
                    ]))
            command = (input(colorama.Fore.YELLOW +
                             f"{UserID} Command: ")
                       .lower())
            if command == "exit":  # exits back to multihandler menu
                break
            try:  # calls command
                if command == "shell":
                    self.beaconCommands.shell(UserID, IPAddress)
                elif command == "close":
                    self.beaconCommands.close_connection(UserID)
                    return
                elif command == "processes":
                    self.beaconCommands.list_processes(UserID)
                elif command == "sysinfo":
                    self.beaconCommands.systeminfo(UserID)
                elif command == "session":
                    for i, details in enumerate(beacons["uuid"]):
                        if details == UserID:
                            if beacons["uuid"][i] == UserID:
                                print(colorama.Fore.GREEN +
                                    "Beacon will change to session mode after the next callback")
                                # send session command to beacon
                                add_beacon_command_list(UserID, "session")
                                # remove the beacon from the list
                                remove_beacon_list(beacons["uuid"][i])
                        return
                elif not exec(command):
                    print((colorama.Fore.GREEN +
                           "NEED TO ADD HELP MENU"))
            except (KeyError, SyntaxError, AttributeError) as e:
                # if the command is not matched then it prints help menu
                print(colorama.Fore.RED + str(e) + "Error HERE")
        return


    def listconnections(self) -> None:
        """
        List all active connections stored in the global objects variables
        """
        if len(sessions["address"]) == 0:  # no connections
            print(colorama.Fore.RED + "No Active Sessions")
        else:
            print("Sessions:")
            for i in range(len(sessions["address"])):
                print(
                    colorama.Fore.GREEN + f"{sessions['uuid'][i]} {sessions['hostname'][i]} {sessions['address'][i]} {sessions['operating_system'][i]}")

        if len(beacons["address"]) == 0:
            print(colorama.Fore.RED + "No Active Beacons")
        else:
            print("Beacons:")
            for i in range(len(beacons["address"])):  # print beacons
                print(
                    colorama.Fore.GREEN +
                    f"{i+1} Host: {beacons['hostname'][i]} " +
                    f"OS: {beacons['operating_system'][i]} " +
                    f"IP: {beacons['address'][i]} " +
                    f"ID: {beacons['uuid'][i]} " +
                    f"Last Callback: {beacons['last_beacon'][i]} ")
                try:
                    next_beacon_time = time.strptime(beacons["next_beacon"][i])
                    current_time = time.strptime(time.asctime())

                    if time.mktime(current_time) > time.mktime(next_beacon_time):
                        time_diff = time.mktime(current_time) - time.mktime(next_beacon_time)
                        print(colorama.Fore.RED + f"Expected Callback was {beacons['next_beacon'][i]}. It is {int(time_diff)} seconds late.")
                    else:   
                        print(colorama.Fore.GREEN + f"Next Callback expected {beacons['next_beacon'][i]} in {time.mktime(next_beacon_time) - time.mktime(current_time)} seconds")
                except ValueError:
                    print(colorama.Fore.YELLOW + "Awaiting first call")
                    
                    
    def sessionconnect(self) -> None:
        """allows interaction with individual session,
            passes connection details through to the current_client function"""
        try:
            if len(sessions["uuid"]) == 1:
                self.current_client_session(
                    sessions["details"][0],
                    sessions["address"][0],
                    sessions["uuid"][0])
            else:               
                data = int(input("What client? "))
                self.current_client_session(
                    sessions["details"][data],
                    sessions["address"][data],
                    sessions["uuid"][data])
        except (IndexError, ValueError):
            print(
                colorama.Fore.WHITE +
                colorama.Back.RED +
                "Not a Valid Client")
        return
                
    def close_all_connections(
            self,
            connection_details: list,
            connection_address: list) -> None:
        """
        close all connections and remove the details
        from the lists in global objects
        """
        error = False
        for i, conn in enumerate(connection_details):
            try:
                send_data(conn, "shutdown")
                if receive_data(conn) == "ack":
                    conn.shutdown(socket.SHUT_RDWR)
                    conn.close()  # closes connection
                if not config["server"]["quiet_mode"]:
                    print(
                        colorama.Back.GREEN +
                        f"Closed {connection_address[i]}")
            except Exception as e:  # handles ssl.SSLEOFError
                if not config["server"]["quiet_mode"]:
                    # user message
                    print(colorama.Back.RED +
                          f"Error Closing + {connection_address[i]}")
                    print(colorama.Back.RED + str(e))
                error = True
                pass
        sessions.clear()
        if not error:
            print(
                colorama.Back.GREEN +
                "All connections closed")  # user message
        else:
            print(colorama.Back.RED + "Not all connections could be closed")
        return

    def close_from_multihandler(
            self,
            connection_details: list,
            connection_address: list) -> None:
        """allows an indiviudal client to be closed the multi handler menu"""
        try:
            # socker to close
            data = int(input("What client do you want to close? "))
            self.sessioncommands.close_connection(
                sessions.connection_details[data],
                sessions.connection_address[data])
            remove_connection_list(
                connection_address[data])  # removes data from lists
            print(colorama.Back.GREEN + "Connection Closed")  # success message
        except ValueError:
            # not a valid connection message
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
        # initalise variables
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
        if str(
            self.database.search_query(
                "*",
                "Hashes",
                "Hash",
                hashedFile)) == "None":  # search database
            self.database.insert_entry(
                "Hashes", f'"{file}","{hashedFile}"')
        return
