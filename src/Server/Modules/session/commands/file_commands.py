# Modules/session/commands/file_commands.py

import ssl
import os
from tqdm import tqdm
import colorama
from ..transfer import send_data, receive_data, send_data_loadingbar
from ...global_objects import logger

class FileCommands:
    """Handles file operation commands."""

    def DownloadFiles(self, conn: ssl.SSLSocket) -> None:
        """Downloads a file from the client to the server."""
        logger.info("Initiating file download from client.")
        send_data(conn, "send_file")
        
        filename = input("What file do you want to download? ")
        send_data(conn, filename)
        logger.info(f"Requested file '{filename}' from client.")
        
        file_basename = os.path.basename(filename)
        data = receive_data(conn)
        
        if isinstance(data, str) and data.startswith("Error:"):
            print(colorama.Back.RED + data)
            logger.error(f"Error downloading file: {data}")
        else:
            with open(file_basename, "wb") as f:
                f.write(data)
            print(colorama.Back.GREEN + f"File '{file_basename}' Downloaded Successfully.")
            logger.info(f"File '{file_basename}' downloaded.")
        return

    def UploadFiles(self, conn: ssl.SSLSocket) -> None:
        """Uploads a file from the server to the client."""
        logger.info("Initiating file upload to client.")
        send_data(conn, "recv_file")
        
        filename = input("What file do you want to upload? ")
        logger.info(f"User requested to upload file: {filename}")

        try:
            with open(filename, "rb") as f:
                send_data(conn, os.path.basename(filename))
                send_data_loadingbar(conn, f.read())
            
            logger.info(f"File '{filename}' sent to client.")
            print(colorama.Back.GREEN + "File uploaded. Waiting for client confirmation...")
            
            confirmation = receive_data(conn)
            if confirmation == "True":
                print(colorama.Back.GREEN + "File received successfully by client.")
                logger.info(f"Confirmation received for {filename}.")
            else:
                print(colorama.Back.RED + "Client reported an issue receiving the file.")
                logger.error(f"Client-side error for file {filename}.")

        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            print(colorama.Back.RED + "File does not exist.")
            send_data(conn, "break")
        except (PermissionError, IsADirectoryError) as e:
            logger.error(f"File access error for '{filename}': {e}")
            print(colorama.Back.RED + f"Cannot access file: {e}")
            send_data(conn, "break")
        return

    def checkfiles(self, conn: ssl.SSLSocket) -> None:
        """Checks client files against known hashes in the database."""
        logger.info("Checking files against database hashes.")
        send_data(conn, "checkfiles")
        
        path_to_check = input("What file or directory do you want to check? ")
        send_data(conn, path_to_check)

        length_str = receive_data(conn)
        if not length_str.isdigit():
            print(colorama.Back.RED + f"Error from client: {length_str}")
            return
            
        length = int(length_str)
        errors, missing_hashes = [], []

        print(colorama.Back.GREEN + f"Checking {length} files...")
        with tqdm(total=length, desc="Files Hashed", colour="#39ff14") as pbar:
            for _ in range(length):
                file_name = receive_data(conn)
                if file_name == "break": break
                
                hashed_value = receive_data(conn)
                
                if file_name == "Error":
                    errors.append(hashed_value)
                    logger.error(f"Client-side error: {hashed_value}")
                else:
                    if str(self.database.search_query("*", "Hashes", "Hash", hashed_value)) == "None":
                        missing_hashes.append(f"'{file_name}' hash is not in the database.")
                pbar.update(1)

        if errors:
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + "Client-side errors occurred:")
            for msg in errors: print(f"- {msg}")
        if missing_hashes:
            print(colorama.Back.RED + "The following files did not match known hashes:")
            for msg in missing_hashes: print(f"- {msg}")
        if not errors and not missing_hashes:
            print(colorama.Back.GREEN + "All file hashes match a hash in the database.")
        return