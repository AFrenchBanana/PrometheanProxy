"""
multi handler commands. Functions to complete tasks within the multi handler menu. 
conn and r_address variables are , connection and address variables fed in from the specified socket.
this allows for multiple connections to be interacted with.
"""

from Modules.sessions_commands import SessionCommandsClass
from Modules.content_handler import TomlFiles
from ServerDatabase.database import DatabaseClass
from Modules.global_objects import remove_connection_list, connectionaddress, connectiondetails, hostname, execute_local_comands, send_data, receive_data, config, tab_compeletion

from typing import Tuple

import hashlib
import os
import tqdm
import colorama
import socket
import readline
import ssl

class MultiHandlerCommands:
    """ class with  multihandler commands, each multi handler can call the class and have access to the commands"""
    # loads the config file into memory
    def __init__(self) -> None:
        self.sessioncommands = SessionCommandsClass() # loads session command class
        self.database = DatabaseClass() # loads database class
        colorama.init(autoreset=True) # resets colorama after each statement
        return
        
    def current_client(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """function that interacts with an individual session, from here commands on the target can be run as documented in the config
        the functions are stored in the SessionCommands.py file"""
        #available_commands = WordCompleter(['shell', 'close', 'processes', 'sysinfo', 'close', 'checkfiles', 'download', 'upload', 'services', 'netstat', 'diskusage', 'listdir'])
        while True: 
            colorama.init(autoreset=True) # resets colorama after each statement
            readline.parse_and_bind("tab: complete")
            readline.set_completer(lambda text, state: tab_compeletion(text, state, ["shell", "close", "processes", "sysinfo", "close", "checkfiles", "download", "upload", "services", "netstat", "diskusage", "listdir"]))
            command = (input(colorama.Fore.YELLOW + f"{r_address[0]}:{r_address[1]} Command: ").lower()) # asks uses for command
            if command == "exit": # exits back to multihandler menu
                break
            try: # calls command
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
                elif not execute_local_comands(command):
                    print((colorama.Fore.GREEN + config['SessionModules']['help']))
            except (KeyError, SyntaxError, AttributeError):
                print((colorama.Fore.GREEN + config['SessionModules']['help'])) #if the command is not matched then it prints help menu
        return
    
    def listconnections(self, connectionaddress: list) -> None:   
        """List all active connections stored in the global objects variables"""  
        if len(connectionaddress) == 0: # no connections
            print(colorama.Fore.RED +"No Active Sessions")
        else:
            print("Sessions:")
            for i, address in enumerate(connectionaddress): # loops through
                print(colorama.Fore.GREEN + f"{i}: {address[0]}:{address[1]} - {hostname[i]}") # i is the index in enumerate, address[0] is the IP and [1] is the port
        return
    

    def sessionconnect(self, connection_details: list, connection_address: list) -> None:
        """allows interaction with individual session, 
            passes connection details through to the current_client function""" 
        try:           
            data = int(input("What client? "))
            self.current_client(connection_details[data], connection_address[data]) # connects to the client socket with appropiate socket input
        except (IndexError, ValueError): # if wrong character or out of range connection 
            print(colorama.Fore.WHITE + colorama.Back.RED + "Not a Valid Client")
        return  
    
    
    def close_all_connections(self, connection_details: list, connection_address: list) -> None:
        """close all connections and remove the details from the lists in global objects"""
        error = False
        for i, conn in enumerate(connection_details): # takes each connection 
            try:
                send_data(conn, "shutdown")
                if receive_data(conn) == "ack":
                    conn.shutdown(socket.SHUT_RDWR) # shutdown the SSL socket
                    conn.close() # closes connection
                if not config["server"]["quiet_mode"]:
                    print(colorama.Back.GREEN + f"Closed {connection_address[i]}") # user message
            except Exception as e: #handles ssl.SSLEOFError
                if not config["server"]["quiet_mode"]:
                    print(colorama.Back.RED + f"Error Closing + {connection_address[i]}") # user message
                    print(colorama.Back.RED + str(e))
                error = True
                pass
        connectionaddress.clear() 
        connectiondetails.clear()
        hostname.clear()
        if not error:
            print(colorama.Back.GREEN + "All connections closed") # user message
        else: 
            print(colorama.Back.RED + f"Not all connections could be closed")
        return


    def close_from_multihandler(self, connection_details: list, connection_address: list) -> None:
        """allows an indiviudal client to be closed the multi handler menu"""
        try:
            data = int(input("What client do you want to close? ")) #socker to close
            self.sessioncommands.close_connection(connection_details[data], connection_address[data]) # closes connection  
            remove_connection_list(connection_address[data]) # removes data from lists
            print(colorama.Back.GREEN + "Connection Closed") # success message
        except ValueError:
            print(colorama.Back.RED + "Not a valid connection") # not a valid connection message
        except IndexError:
            pass 
        return
    
    
    def localDatabaseHash(self) -> None:
        """allows local files to be hased and stored in the database. 
        Has the ability to check check if its a directory or file and respond accordingly"""
        dir = input("What directory or file do you want to hash?: ") # ask for file/ directory to be hashed
        # initalise variables
        length = 0 
        fileList = []
        try: # attempts to hash as if the file is a directory
            try:
                files = os.scandir(dir) # get a list of objects in the directory
                for entry in files:
                    try:
                        if entry.is_file(): # check if its a file
                            length += 1 # number of files 
                            fileList.append(entry.name) # appends file name to the list
                    except PermissionError: # pass file if dont have permission
                        pass 
            except PermissionError: # returns permission error if unable to open
                print(colorama.Back.RED + "Permission Error") #permission error on whole directory
            # for loop for each file, makes a loading bar with the length variable
            for i in tqdm.tqdm(range(0, length), desc ="Files Hashed", colour="#39ff14"): 
                try: # attempts to hash the file
                    self.hashfile(f"{dir}/{fileList[i]}") #calls hash file functio nwith the full path
                except (IsADirectoryError, PermissionError): # error handling 
                    pass 
                i += 1 # increment loading bar +1 
            print(colorama.Back.GREEN + ("Files Hashed")) # user message
        except NotADirectoryError: # if the intial message is a file this error will return
                try:
                    self.hashfile(dir) # hash single file
                    print(colorama.Back.GREEN + ("File Hashed")) # return hash
                except PermissionError: # permission error on file
                    print(colorama.Back.RED + f"Permission error on {dir}") # error message print
        except (IsADirectoryError, FileNotFoundError): 
            print(colorama.Back.RED + "File or Directory Does not exist") # print error message


    def hashfile(self, file: str) -> None :
        """hashes a file fed into it and calls the datbase function to add to the database"""
        with open(file, 'rb') as directoryFiles: # opens the file 
            #hashes as sha256 and sends into addHashToDatabase
            self.addHashToDatabase(file, hashlib.sha256(directoryFiles.read(os.path.getsize(file))).hexdigest())
            directoryFiles.close() #closes file
            return
    

    def addHashToDatabase(self, file: str, hashedFile: str) -> None:
        """checks if the hash is in the database, if not adds it to the database """
        if str(self.database.search_query("*", "Hashes",  "Hash", hashedFile)) == "None": #search database
                self.database.insert_entry("Hashes", f'"{file}","{hashedFile}"') # add to database if unique
        return