
from ...global_objects import logger

import os
import tqdm
import colorama
import hashlib


class DatabaseHandler:
    """Handles local file hashing and database commands."""

    def localDatabaseHash(self) -> None:
        """
        Hashes local files or directories and stores the hashes in the database.
        """
        logger.info("Starting local database hash process")
        dir_path = input("Enter the directory or file path to hash: ")
        
        try:
            # Handle directory
            if os.path.isdir(dir_path):
                file_list = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
                if not file_list:
                    print(colorama.Fore.YELLOW + f"No files found in directory '{dir_path}'.")
                    return

                print(f"Found {len(file_list)} files to hash.")
                with tqdm.tqdm(total=len(file_list), desc="Files Hashed", colour="#39ff14") as pbar:
                    for file_path in file_list:
                        try:
                            self.hashfile(file_path)
                        except PermissionError:
                            logger.warning(f"Permission denied for file: {file_path}")
                        pbar.update(1)
                print(colorama.Back.GREEN + "Directory hashing complete.")

            # Handle single file
            elif os.path.isfile(dir_path):
                logger.info(f"Hashing single file: {dir_path}")
                self.hashfile(dir_path)
                print(colorama.Back.GREEN + "File Hashed.")

            # Handle not found
            else:
                logger.error(f"File or directory does not exist: {dir_path}")
                print(colorama.Back.RED + "File or Directory does not exist.")
        
        except PermissionError:
            logger.error(f"Permission error accessing path: {dir_path}")
            print(colorama.Back.RED + f"Permission error accessing '{dir_path}'.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during hashing: {e}")
            print(colorama.Back.RED + "An unexpected error occurred.")


    def hashfile(self, file_path: str) -> None:
        """
        Hashes a single file and calls the database function to add the hash.
        """
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            self.addHashToDatabase(file_path, sha256_hash)
            logger.info(f"Hashed file: {file_path}")
        return

    def addHashToDatabase(self, file_path: str, hashed_file: str) -> None:
        """
        Checks if a hash is in the database; if not, it adds it.
        """
        logger.info(f"Adding hash for file: {file_path}")
        
        result = self.database.search_query(
            "Hash", "Hashes", "Hash", f'"{hashed_file}"'
        )

        if not result:
            logger.info(f"Hash not found. Adding new entry for file: {file_path}")
            self.database.insert_entry(
                "Hashes", f'"{file_path}", "{hashed_file}"'
            )
        else:
            logger.info(f"Hash already exists in the database.")
        return