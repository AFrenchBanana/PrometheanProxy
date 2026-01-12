from ...global_objects import logger

import os
import tqdm
import colorama
import hashlib
import os

from ...global_objects import logger
from ...utils.ui_manager import RichPrint
from ...utils.console import colorize


class DatabaseHandler:
    """
    Handles database-related commands for the multi-handler module.
    """

    def localDatabaseHash(self) -> None:
        """
        Hashes files or directories locally and stores the hashes in the database.
        """
        logger.info("Starting local database hash process")
        dir_path = self.prompt_session.prompt(
            "Enter the directory or file path to hash: "
        )

        try:
            # Handle directory
            if os.path.isdir(dir_path):
                file_list = [
                    os.path.join(dir_path, f)
                    for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                if not file_list:
                    RichPrint.r_print(
                        colorize(
                            f"No files found in directory '{dir_path}'.", fg="yellow"
                        )
                    )
                    return

                RichPrint.r_print(f"Found {len(file_list)} files to hash.")
                with tqdm.tqdm(
                    total=len(file_list), desc="Files Hashed", colour="#39ff14"
                ) as pbar:
                    for file_path in file_list:
                        try:
                            self.hashfile(file_path)
                        except PermissionError:
                            logger.warning(f"Permission denied for file: {file_path}")
                        pbar.update(1)
                RichPrint.r_print(colorize("Directory hashing complete.", bg="green"))

            # Handle single file
            elif os.path.isfile(dir_path):
                logger.info(f"Hashing single file: {dir_path}")
                self.hashfile(dir_path)
                RichPrint.r_print(colorize("File Hashed.", bg="green"))

            # Handle not found
            else:
                logger.error(f"File or directory does not exist: {dir_path}")
                RichPrint.r_print(
                    colorize("File or Directory does not exist.", bg="red")
                )

        except PermissionError:
            logger.error(f"Permission error accessing path: {dir_path}")
            RichPrint.r_print(
                colorize(f"Permission error accessing '{dir_path}'.", bg="red")
            )
            RichPrint.r_print(colorize("An unexpected error occurred.", bg="red"))

    def hashfile(self, file_path: str) -> None:
        """
        Hashes a single file and adds the hash with sha256 and adds to the database.
        """
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            self.addHashToDatabase(file_path, sha256_hash)
            logger.info(f"Hashed file: {file_path}")
        return

    def addHashToDatabase(self, file_path: str, hashed_file: str) -> None:
        """
        Adds a file hash to the database if it does not already exist.
        """
        logger.info(f"Adding hash for file: {file_path}")

        result = self.database.search_query(
            "Hash", "Hashes", "Hash", f'"{hashed_file}"'
        )

        if not result:
            logger.info(f"Hash not found. Adding new entry for file: {file_path}")
            self.database.insert_entry("Hashes", f'"{file_path}", "{hashed_file}"')
        else:
            logger.info(f"Hash already exists in the database.")
        return
