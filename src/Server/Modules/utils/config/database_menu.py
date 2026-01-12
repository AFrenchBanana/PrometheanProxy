"""
Database Menu Module - Database Management Functions

Provides the database management menu and related functions
for managing command and user databases.
"""

from prompt_toolkit.completion import WordCompleter
from rich.box import ROUNDED
from rich.table import Table

from ...global_objects import config as loadedConfig
from ...global_objects import logger
from ..content_handler import TomlFiles
from ..ui import (
    create_database_config_table,
    create_menu_table,
    create_tables_list_table,
    get_ui_manager,
)
from .shared import CONFIG_FILE_PATH, get_prompt_session


def database_management_menu() -> None:
    """
    Database management menu with modern UI.

    Provides options for managing both command and user databases
    including viewing config, clearing tables, and toggling persistence.
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()

    from ServerDatabase.database import DatabaseClass

    from ...global_objects import command_database

    # Initialize user database
    user_database = DatabaseClass(loadedConfig, "user_database")

    menu_options = {
        "1": "Show Database Config",
        "2": "Clear Command Database Tables",
        "3": "Clear User Database Tables",
        "4": "Clear Specific Table",
        "5": "List All Tables",
        "6": "Toggle Persistent Beacons",
        "7": "Toggle Persistent Sessions",
        "8": "Exit Menu",
    }

    completer = WordCompleter(
        [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "exit",
            "config",
            "clear",
            "tables",
            "persist",
            "quit",
            "q",
        ]
    )

    while True:
        logger.debug("Database management menu started")
        ui.print("")
        ui.console.print(create_menu_table("Database Management", menu_options))
        ui.print("")

        try:
            inp = prompt_session.prompt(
                "Database ❯ ",
                completer=completer,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return

        if inp in ["1", "config"]:
            show_database_config()

        elif inp == "2":
            clear_database(command_database, "command database")

        elif inp == "3":
            clear_database(user_database, "user database")

        elif inp == "4":
            clear_specific_table(command_database, user_database)

        elif inp in ["5", "tables"]:
            list_all_tables(command_database, user_database)

        elif inp in ["6", "persist"]:
            toggle_persistence("persist_beacons", "beacons")

        elif inp == "7":
            toggle_persistence("persist_sessions", "sessions")

        elif inp in ["8", "exit", "quit", "q"]:
            logger.debug("Exiting database management menu")
            return
        else:
            ui.print_error(f"Invalid option: '{inp}'")


def show_database_config() -> None:
    """Display current database configuration settings."""
    ui = get_ui_manager()
    logger.debug("Showing database configuration")

    # Get database configs
    cmd_db_config = loadedConfig.get("command_database", {})
    user_db_config = loadedConfig.get("user_database", {})

    # Display the config table
    table = create_database_config_table(cmd_db_config, user_db_config)
    ui.console.print(table)

    # Show persistence status summary
    persist_beacons = cmd_db_config.get("persist_beacons", True)
    persist_sessions = cmd_db_config.get("persist_sessions", True)

    ui.print("")
    if persist_beacons:
        ui.print_success(
            "Beacon persistence: [bright_green]ENABLED[/] - Beacons will be saved to database"
        )
    else:
        ui.print_warning(
            "Beacon persistence: [bright_red]DISABLED[/] - Beacons will not be saved"
        )

    if persist_sessions:
        ui.print_success(
            "Session persistence: [bright_green]ENABLED[/] - Sessions will be saved to database"
        )
    else:
        ui.print_warning(
            "Session persistence: [bright_red]DISABLED[/] - Sessions will not be saved"
        )


def clear_database(database, db_name: str) -> None:
    """
    Clear all tables in a database with confirmation.

    Args:
        database: Database instance to clear
        db_name: Human-readable name of the database
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug(f"Clearing all tables in {db_name}")

    if not database:
        ui.print_error(f"{db_name.title()} not available")
        return

    try:
        confirm = (
            prompt_session.prompt(
                f"[bright_red]Clear ALL tables in {db_name}?[/] (type 'yes' to confirm) ❯ "
            )
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled")
        return

    if confirm == "yes":
        try:
            if database.clear_all_tables():
                ui.print_success(f"Cleared all tables in {db_name}")
                logger.info(f"Cleared all tables in {db_name}")
            else:
                ui.print_error(f"Failed to clear tables in {db_name}")
        except Exception as e:
            logger.error(f"Error clearing {db_name}: {e}")
            ui.print_error(f"Error: {e}")
    else:
        ui.print_info("Cancelled")


def clear_specific_table(command_database, user_database) -> None:
    """
    Clear a specific table with selection menu.

    Args:
        command_database: Command database instance
        user_database: User database instance
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug("Clearing specific table")

    # Select database
    db_completer = WordCompleter(["1", "2", "command", "user", "cancel"])

    ui.print("\n[bright_cyan]1[/] Command Database")
    ui.print("[bright_cyan]2[/] User Database")

    try:
        db_choice = (
            prompt_session.prompt(
                "Select database ❯ ",
                completer=db_completer,
            )
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled")
        return

    if db_choice in ["1", "command"]:
        db = command_database
        db_name = "command database"
    elif db_choice in ["2", "user"]:
        db = user_database
        db_name = "user database"
    else:
        ui.print_info("Cancelled")
        return

    if not db:
        ui.print_error(f"{db_name.title()} not available")
        return

    try:
        tables = db.get_table_list()
    except Exception as e:
        logger.error(f"Error getting table list: {e}")
        ui.print_error(f"Error: {e}")
        return

    if not tables:
        ui.print_warning(f"No tables found in {db_name}")
        return

    # Show tables
    table_display = Table(
        title=f"[bold bright_cyan]Tables in {db_name.title()}[/]",
        box=ROUNDED,
        border_style="bright_cyan",
    )
    table_display.add_column("#", style="dim", width=4)
    table_display.add_column("Table Name", style="bright_yellow")

    for i, table in enumerate(tables, 1):
        table_display.add_row(str(i), table)

    ui.console.print(table_display)

    try:
        table_choice = prompt_session.prompt("Enter table number ❯ ").strip()
        table_idx = int(table_choice) - 1

        if 0 <= table_idx < len(tables):
            table_name = tables[table_idx]

            confirm = (
                prompt_session.prompt(f"Clear table '{table_name}'? (type 'yes') ❯ ")
                .strip()
                .lower()
            )

            if confirm == "yes":
                try:
                    if db.clear_table(table_name):
                        ui.print_success(f"Cleared table '{table_name}'")
                        logger.info(f"Cleared table {table_name} in {db_name}")
                    else:
                        ui.print_error(f"Failed to clear table '{table_name}'")
                except Exception as e:
                    logger.error(f"Error clearing table: {e}")
                    ui.print_error(f"Error: {e}")
            else:
                ui.print_info("Cancelled")
        else:
            ui.print_error("Invalid table number")
    except (ValueError, EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled")


def list_all_tables(command_database, user_database) -> None:
    """
    List all tables in both databases.

    Args:
        command_database: Command database instance
        user_database: User database instance
    """
    ui = get_ui_manager()
    logger.debug("Listing all tables")

    # Get table lists
    cmd_tables = []
    user_tables = []

    if command_database:
        try:
            cmd_tables = command_database.get_table_list() or []
        except Exception as e:
            logger.error(f"Error getting command database tables: {e}")

    if user_database:
        try:
            user_tables = user_database.get_table_list() or []
        except Exception as e:
            logger.error(f"Error getting user database tables: {e}")

    # Display the table
    table = create_tables_list_table(cmd_tables, user_tables)
    ui.console.print(table)

    # Show counts
    ui.print("")
    ui.print_info(f"Command database: [bright_cyan]{len(cmd_tables)}[/] tables")
    ui.print_info(f"User database: [bright_cyan]{len(user_tables)}[/] tables")


def toggle_persistence(setting: str, item_type: str) -> None:
    """
    Toggle a persistence setting.

    Args:
        setting: The setting key name (e.g., "persist_beacons")
        item_type: Human-readable type name (e.g., "beacons")
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug(f"Toggling {setting}")

    current_value = loadedConfig.get("command_database", {}).get(setting, True)
    new_value = not current_value

    status = "[bright_green]enabled[/]" if current_value else "[bright_red]disabled[/]"
    new_status = "[bright_green]enabled[/]" if new_value else "[bright_red]disabled[/]"

    ui.print(f"\nPersistent {item_type}: {status}")

    try:
        confirm = (
            prompt_session.prompt(f"Change to {new_status}? (y/N) ❯ ").strip().lower()
        )
    except (EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled")
        return

    if confirm in ["y", "yes"]:
        try:
            toml_file = TomlFiles(CONFIG_FILE_PATH)
            toml_file.update_config("command_database", setting, new_value)

            if "command_database" not in loadedConfig:
                loadedConfig["command_database"] = {}
            loadedConfig["command_database"][setting] = new_value

            ui.print_success(f"Persistent {item_type} is now {new_status}")
            ui.print_info(f"Note: Only affects new {item_type}")
            logger.info(f"Updated command_database.{setting} to {new_value}")
        except Exception as e:
            logger.error(f"Error updating persistence setting: {e}")
            ui.print_error(f"Failed to update setting: {e}")
    else:
        ui.print_info("Cancelled")


def get_persistence_status() -> dict:
    """
    Get the current persistence status for beacons and sessions.

    Returns:
        Dictionary with persist_beacons and persist_sessions values
    """
    cmd_db_config = loadedConfig.get("command_database", {})
    return {
        "persist_beacons": cmd_db_config.get("persist_beacons", True),
        "persist_sessions": cmd_db_config.get("persist_sessions", True),
    }


def set_persistence(item_type: str, enabled: bool) -> bool:
    """
    Set a persistence setting programmatically.

    Args:
        item_type: "beacons" or "sessions"
        enabled: True to enable persistence, False to disable

    Returns:
        bool: True if successful
    """
    setting = f"persist_{item_type}"

    try:
        toml_file = TomlFiles(CONFIG_FILE_PATH)
        toml_file.update_config("command_database", setting, enabled)

        if "command_database" not in loadedConfig:
            loadedConfig["command_database"] = {}
        loadedConfig["command_database"][setting] = enabled

        logger.info(f"Set {setting} to {enabled}")
        return True
    except Exception as e:
        logger.error(f"Failed to set {setting}: {e}")
        return False
