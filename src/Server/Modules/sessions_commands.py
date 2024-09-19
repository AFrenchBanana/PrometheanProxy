from ServerDatabase.database import DatabaseClass
from Modules.content_handler import TomlFiles
from Modules.global_objects import send_data, receive_data, remove_connection_list, send_data_loadingbar, execute_local_comands, config
from datetime import datetime
from tqdm import tqdm
from typing import Tuple

import os
import colorama
import ssl 



class SessionCommandsClass:
    """Handles commands within a session"""
    def __init__(self) -> None:
        self.database = DatabaseClass() # laods database class
        colorama.init(autoreset=True) # resets colorama after each function
        


    def close_connection(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """closes connection from the current session within the session commands"""
        #confirmation to close connection
        if input(colorama.Back.RED + "Are you sure want to close the connection?: Y/N ").lower() == "y": 
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + f"Closing {r_address[0]}:{r_address[1]}")
            try:
                send_data(conn, "shutdown") # sends shutdown mesage to client
            except: #handles ssl.SSLEOFError
                pass
            remove_connection_list(r_address) # removes connection from lists
            conn.close() # closes conneciton
            print(colorama.Back.GREEN + "Closed") # user message
        else:
            print(colorama.Back.GREEN + "Connection not closed") # user message
        return
    

    def shell(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """runs a shell between the sessions client and server"""
        print(f"Shell {r_address[0]}:{r_address[1]}: Type exit to quit session") 
        send_data(conn, "shell") # calls the shell command on the client
        details = receive_data(conn) # get the current working directory and username of the client
        username, cwd = details.split("<sep>") # splits the data based on the seperator
        while True:
            command = input(f"{username}@{r_address[0]}:{r_address[1]}-[{cwd}]: ") # ask for user command
            if not command.strip(): 
                continue
            send_data(conn, command) # send the command to the client
            if command.lower() == "exit": # check if the command is exit
                break
            output = receive_data(conn)  # sets output based on recieved data
            results, _, cwd = output.rpartition("<sep>")# splits the working directory and result
            self.database.insert_entry("Shell", f"'{r_address[0]}','{datetime.now()}', '{command}', '{results}'") # adds to database
            print(results) # prints result
        return


    def list_processes(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """list processes running on client"""
        send_data(conn, "list_processes") # calls the list processes command on client
        processes = receive_data(conn) # recieves results
        self.database.insert_entry("Processes", f'"{r_address[0]}","{processes}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') #inserts to database
        print(processes) # prints results
        return


    def systeminfo(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """gets the systeminfo of the client"""
        send_data(conn,"systeminfo") # sends the system info command to start the process
        data = receive_data(conn) # recives data 
        print(data) # prints the results
        self.database.insert_entry("SystemInfo", f'"{r_address[0]}","{data}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') # inserts the entry
        return
    

    def checkfiles(self, conn: ssl.SSLSocket) -> None:
        """checks files against known hashes in the database """
        send_data(conn,"checkfiles") # call the check files function on the client 
        send_data(conn, input("What File do you want to check? ")) # ask what files wants to be checked
        length = receive_data(conn) # recieves the number of files being checked
        # initalise the variables
        errors = []
        missinghashes = []
        file_name = ""
        Error = False
        nomatch = False
        print(colorama.Back.GREEN + f"Checking {length} files") # tells user how many files are being checked
        for i in tqdm(range(0, int(length)), desc ="Files Hashes", colour="#39ff14"): # loading bar for range of files
            file_name = receive_data(conn) # recives the filename
            if file_name == "break": # break means all files are done or error
                break 
            hashed = receive_data(conn) # recieves hashed file
            if file_name == "Error": # if an error has occured
                errors.append(hashed) # had message to error list
                Error = True #ensures the errors are printed
            else:
                if str(self.database.search_query("*", "Hashes",  "Hash", hashed)) == "None": # checks if hash is in the database
                    missinghashes.append(f"{file_name} is not in the database") # if its missing add the file name to list 
                    nomatch = True # prints matches at the end
            i += 1 # filenumber + 1
        if Error == True: # prints error messages
            for message in errors:
                print(colorama.Back.YELLOW + colorama.Fore.BLACK + message)
        if nomatch == True: # prints missing hashes
            for message in missinghashes:
                print(colorama.Back.RED + message)
        else:
            print(colorama.Back.GREEN + "All hashes match a hash in the database") # all hashes good
        return

        
    def DownloadFiles(self, conn: ssl.SSLSocket) -> None:
        """ Function downloads a files from the client to the server"""
        send_data(conn, "send_file") # calls the send files function on the client
        filename = input("What file do you want to download? ") # asks what file the user wants to download
        send_data(conn, filename) # sends the filename
        filename = os.path.basename(filename) # gets the basename of the file to write too
        data = receive_data(conn) # recieves file data
        if data == "Error": # if the data is error, print an error message
            print(colorama.Back.RED + receive_data(conn))
        else:
            if isinstance(data, str): # if its a string encode it (for text files)
                data = data.encode()
            with open(filename, "wb") as f: # write the files as bytes to the file name
                f.write(data)
                f.close() # close the file
            print(colorama.Back.GREEN + "File Downloaded") # Confirmation method
        return


    def UploadFiles(self, conn: ssl.SSLSocket) -> None:
        """upload files from the server to the client"""
        send_data(conn, "recv_file") #call teh recv_file funciton on the client
        filename = input("What file do you want to upload? ") # ask what file to upload
        try:
            with open(filename, "rb") as f:# open the file name
                send_data(conn, os.path.basename(filename))
                send_data_loadingbar(conn, f.read(os.path.getsize(filename))) # send the file to the client
                f.close()
            print(colorama.Back.GREEN + "File uploaded") # confirmation method server side
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + "Waiting for confirmation from client")
            if receive_data(conn) == "True": # confirmation method client side
                print(colorama.Back.GREEN + "File recieved succesfully")
            else:
                print(colorama.Back.RED + "File was not received properly")
        except FileNotFoundError: # file not found error
            print(colorama.Back.RED + "File doesn't exist")
            send_data(conn, "break") # cancels upload on client side
            return
        except PermissionError: # permission error
            print(colorama.Back.RED + "You do not have permission to access this file")
            send_data(conn, "break") # cancels upload on client side
        except IsADirectoryError:
            print(colorama.Back.RED + "This is a directory") # directory error
            send_data(conn, "break") # cancels upload on client side
        return


    def list_services(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """lists services on the client"""
        send_data(conn, "list_services") # calls list_services function on the client
        services = receive_data(conn) # recieve the services
        self.database.insert_entry("Services", f'"{r_address[0]}","{services}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') # insert data to database
        print(services) # prints the services
        return


    def netstat(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """prints netstat details from the client"""
        netstat = "" # intialises variable
        send_data(conn, "netstat") # calls netstat function on the client side
        while True:
            data = receive_data(conn) # recives data
            if data == "break": # last line 
                break
            netstat += data # adds line of data to string
        print(colorama.Fore.YELLOW + netstat) # prints netstat
        self.database.insert_entry("Netstat", f'"{r_address[0]}","{netstat}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') #inserts entry to database
        return


    def diskusage(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """prints the diskuage for the client"""
        send_data(conn, "disk_usage") #calls the disk_usuage function on the client
        results = receive_data(conn) # saves the results
        self.database.insert_entry("Disk", f'"{r_address[0]}","{results}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') # inserts to database
        print(colorama.Fore.YELLOW + results) # prints results


    def list_dir(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """list a directory on the client"""
        send_data(conn, "list_dir") #calls the list_dir function on the clietn
        dir = input("What directory do you want to list?: ") # ask what directory to list
        send_data(conn, dir) # sends the directory
        directory = receive_data(conn) # recives processed data
        if str(directory).startswith("Error:"): # if the data is an error pass
            pass
        else:
            try:
                self.database.insert_entry("Shell", f'"{r_address[0]}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}", "ls {dir}", "{directory}"') # insert to database
            except:
                pass
        print(directory) # print directory
