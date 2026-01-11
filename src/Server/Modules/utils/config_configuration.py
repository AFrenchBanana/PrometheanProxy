import readline
from tabulate import tabulate

from .content_handler import TomlFiles
from ..global_objects import tab_completion
import ipaddress

from ..global_objects import config as loadedConfig, logger

CONFIG_FILE_PATH = 'config.toml'


def config_menu() -> None:
    logger.debug("Config menu started")
    while True:
        print("Config Menu")
        print("1. Show Config")
        print("2. Edit Config")
        print("3. Database Management")
        print("4. Exit")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, [
                    "1", "2", "3", "4"]))
        inp = input("Enter Option: ")
        if inp == "1":
            logger.debug("Showing config")
            list(map(lambda x: show_config(x), ["server", "authentication",
                                                "packetsniffer", "beacon"]))
        if inp == "2":
            logger.debug("Editing config")
            edit_config()
        if inp == "3":
            logger.debug("Opening database management menu")
            database_management_menu()
        if inp == "4":
            logger.debug("Exiting config menu")
            return


def show_config(indexKey) -> None:
    print(f"Configuration for {indexKey}")
    config = loadedConfig.get(indexKey, {})
    logger.debug(f"Showing config for {indexKey}: {config}")
    if not config:
        logger.warning(f"No configuration found for {indexKey}")
        print("No configuration found.")
        return
    table = [[key, value] for key, value in config.items()]
    logger.debug(f"Config table: {table}")
    print(tabulate(table, headers=["Key", "Value"], tablefmt='grid'))


def edit_config() -> bool:
    logger.debug("Starting edit config")
    main_keys = ["server", "authentication", "packetsniffer", "exit"]
    server_keys = [
        "listenaddress",
        "port",
        "TLSCertificateDir",
        "TLSCertificate",
        "TLSkey",
        "GUI",
        "quiet_mode"]
    authentication_keys = ["keylength"]
    packetsniffer_keys = [
        "active",
        "listenaddress",
        "port",
        "TLSCertificate",
        "TLSKey",
        "debugPrint"]
    toml_file = TomlFiles(CONFIG_FILE_PATH)
    with toml_file as config:
        logger.debug("Config file opened for editing")
        while True:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(
                    text, state, main_keys))
            key = input("Enter key: ")
            if key == "exit":
                return False
            if key not in main_keys:
                print("Not a valid key")
                pass
            if key == "server":
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, server_keys))
            elif key == "authentication":
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, authentication_keys))
            elif key == "packetsniffer":
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, packetsniffer_keys))
            subkey = input("Enter sub-key to change: ")
            if subkey not in config[key]:
                print("Invalid subkey")
                logger.warning("Invalid subkey entered: %s", subkey)
                pass
            print("Current value: ", config[key][subkey])
            new_value = input("Enter new value: ")
            if isinstance(config[key][subkey], bool):
                if new_value.lower() not in ["true", "false"]:
                    print("Invalid value. Please enter true or false")
                    logger.warning(
                        "Invalid boolean entered: %s", new_value)
                else:
                    update = True
                    if new_value.lower() == "true":
                        new_value = True
                    else:
                        new_value = False
            elif isinstance(config[key][subkey], int):
                if not new_value.isdigit():
                    print("Invalid value. Please enter a number")
                    logger.warning(
                        "Invalid number entered: %s", new_value)
                else:
                    update = True
            elif subkey == ("listenaddress" and not
                            ipaddress.ip_address(new_value)):
                print("Invalid value. Please enter a valid IP address")
                logger.warning(
                    "Invalid IP address entered: %s", new_value)
            elif (subkey == "port" and not new_value.isdigit() and
                  (int(new_value) < 0 or int(new_value) > 65535)):
                print("Invalid value. Please enter a valid port number")
                logger.warning(
                    "Invalid port number entered: %s", new_value)
                continue
            else:
                update = True
            if update:
                toml_file.update_config(key, subkey, new_value)
                print("Changes saved successfully!")
                print("Restart the server to apply changes.")
                logger.info(f"Updated {key}.{subkey} to {new_value}")
                return True


def edit_beacon_config() -> None:
    logger.debug("Editing beacon config")
    beacon_keys = [
        "interval",
        "jitter",
    ]
    readline.set_completer(
        lambda text, state: tab_completion(
            text, state, beacon_keys))
    key = input("Enter key: ").lower()
    logger.debug(f"Editing beacon config key: {key}")
    if key not in beacon_keys:
        print("Not a valid key")
        logger.warning(f"Invalid beacon key entered: {key}")
        return
    print("""
          Times are in seconds, this will not update live beacons
          only new beacons.
          You can edit live beacons in the beacon menu.
          """)
    print("Current value: ", loadedConfig["beacon"][key])
    readline.set_completer(lambda text, state: tab_completion(
        text, state, ""))
    new_value = input("Enter new value: ")
    logger.debug(f"New value for {key}: {new_value}")
    if isinstance(loadedConfig["beacon"][key], int):
        try:
            new_value = int(new_value)
        except ValueError:
            print("Invalid value. Please enter a number")
            return
    loadedConfig["beacon"][key] = new_value
    logger.info(f"Updated beacon.{key} to {new_value}")
    toml_file = TomlFiles(CONFIG_FILE_PATH)
    toml_file.update_config("beacon", key, new_value)
    print("Changes saved successfully!")


def beacon_config_menu() -> None:
    while True:
        logger.debug("Beacon config menu started")
        print("Beacon Config Menu")
        print("1. Show Beacon Config")
        print("2. Edit Beacon Config")
        print("3. Exit")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, [
                    "1", "2", "3"]))
        inp = input("Enter Option: ")
        logger.debug(f"Beacon config menu input: {inp}")
        if inp == "1":
            logger.debug("Showing beacon config")
            show_config("beacon")
        if inp == "2":
            edit_beacon_config()
            logger.debug("Edited beacon config")
        if inp == "3":
            logger.debug("Exiting beacon config menu")
            return


def database_management_menu() -> None:
    """
    Database Management Menu
    Provides options to clear databases and tables.
    """
    from ..global_objects import command_database
    from ServerDatabase.database import DatabaseClass
    
    # Initialize user database
    user_database = DatabaseClass(loadedConfig, "user_database")
    
    while True:
        logger.debug("Database management menu started")
        print("\nDatabase Management Menu")
        print("=" * 50)
        print("1. Clear All Tables (Command Database)")
        print("2. Clear All Tables (User Database)")
        print("3. Clear Specific Table")
        print("4. List All Tables")
        print("5. Toggle Persistent Beacons")
        print("6. Toggle Persistent Sessions")
        print("7. Exit")
        print("=" * 50)
        
        readline.parse_and_bind("tab: complete")
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, [
                    "1", "2", "3", "4", "5", "6", "7"]))
        
        inp = input("Enter Option: ")
        logger.debug(f"Database management menu input: {inp}")
        
        if inp == "1":
            logger.debug("Clearing all tables in command database")
            confirm = input("Are you sure you want to clear all tables in the command database? (yes/no): ")
            if confirm.lower() == "yes":
                if command_database and command_database.clear_all_tables():
                    print("Successfully cleared all tables in command database.")
                    logger.info("Cleared all tables in command database")
                else:
                    print("Failed to clear tables in command database.")
            else:
                print("Operation cancelled.")
                
        elif inp == "2":
            logger.debug("Clearing all tables in user database")
            confirm = input("Are you sure you want to clear all tables in the user database? (yes/no): ")
            if confirm.lower() == "yes":
                if user_database.clear_all_tables():
                    print("Successfully cleared all tables in user database.")
                    logger.info("Cleared all tables in user database")
                else:
                    print("Failed to clear tables in user database.")
            else:
                print("Operation cancelled.")
                
        elif inp == "3":
            logger.debug("Clearing specific table")
            print("\nSelect Database:")
            print("1. Command Database")
            print("2. User Database")
            db_choice = input("Enter choice: ")
            
            if db_choice == "1":
                db = command_database
                db_name = "command database"
            elif db_choice == "2":
                db = user_database
                db_name = "user database"
            else:
                print("Invalid choice.")
                continue
            
            if not db:
                print(f"Database not available.")
                continue
                
            tables = db.get_table_list()
            print(f"\nAvailable tables in {db_name}:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            table_choice = input("Enter table number to clear: ")
            try:
                table_idx = int(table_choice) - 1
                if 0 <= table_idx < len(tables):
                    table_name = tables[table_idx]
                    confirm = input(f"Are you sure you want to clear table '{table_name}'? (yes/no): ")
                    if confirm.lower() == "yes":
                        if db.clear_table(table_name):
                            print(f"Successfully cleared table '{table_name}'.")
                            logger.info(f"Cleared table {table_name} in {db_name}")
                        else:
                            print(f"Failed to clear table '{table_name}'.")
                    else:
                        print("Operation cancelled.")
                else:
                    print("Invalid table number.")
            except ValueError:
                print("Invalid input.")
                
        elif inp == "4":
            logger.debug("Listing all tables")
            print("\nCommand Database Tables:")
            if command_database:
                for table in command_database.get_table_list():
                    print(f"  - {table}")
            else:
                print("  Command database not available.")
            
            print("\nUser Database Tables:")
            for table in user_database.get_table_list():
                print(f"  - {table}")
                
        elif inp == "5":
            logger.debug("Toggling persistent beacons")
            current_value = loadedConfig.get("command_database", {}).get("persist_beacons", True)
            print(f"\nCurrent setting: persist_beacons = {current_value}")
            new_value = not current_value
            confirm = input(f"Change to {new_value}? (yes/no): ")
            if confirm.lower() == "yes":
                toml_file = TomlFiles(CONFIG_FILE_PATH)
                toml_file.update_config("command_database", "persist_beacons", new_value)
                loadedConfig["command_database"]["persist_beacons"] = new_value
                print(f"persist_beacons set to {new_value}")
                logger.info(f"Updated command_database.persist_beacons to {new_value}")
                print("Note: Existing beacons are not affected. This applies to new beacons only.")
            else:
                print("Operation cancelled.")
                
        elif inp == "6":
            logger.debug("Toggling persistent sessions")
            current_value = loadedConfig.get("command_database", {}).get("persist_sessions", True)
            print(f"\nCurrent setting: persist_sessions = {current_value}")
            new_value = not current_value
            confirm = input(f"Change to {new_value}? (yes/no): ")
            if confirm.lower() == "yes":
                toml_file = TomlFiles(CONFIG_FILE_PATH)
                toml_file.update_config("command_database", "persist_sessions", new_value)
                loadedConfig["command_database"]["persist_sessions"] = new_value
                print(f"persist_sessions set to {new_value}")
                logger.info(f"Updated command_database.persist_sessions to {new_value}")
                print("Note: Existing sessions are not affected. This applies to new sessions only.")
            else:
                print("Operation cancelled.")
                
        elif inp == "7":
            logger.debug("Exiting database management menu")
            return
        else:
            print("Invalid option. Please try again.")

