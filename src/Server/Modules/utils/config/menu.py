"""
Config Menu Module - Main Configuration Menu

Provides the main configuration menu for navigating server settings,
database management, and other configuration options.
"""

from prompt_toolkit.completion import WordCompleter

from ...global_objects import config as loadedConfig
from ...global_objects import logger
from ..ui import create_config_table, create_menu_table, get_ui_manager
from .shared import get_prompt_session


def config_menu() -> None:
    """
    Main configuration menu with modern UI.

    Provides options to view configuration, edit settings,
    and manage database options.
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug("Config menu started")

    menu_options = {
        "1": "Show Configuration",
        "2": "Edit Configuration",
        "3": "Database Management",
        "4": "Exit Menu",
    }

    completer = WordCompleter(
        ["1", "2", "3", "4", "show", "edit", "database", "exit", "quit", "q"]
    )

    while True:
        ui.print("")
        ui.console.print(create_menu_table("Configuration Menu", menu_options))
        ui.print("")

        try:
            inp = (
                prompt_session.prompt(
                    "Config ❯ ",
                    completer=completer,
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            return

        if inp in ["1", "show"]:
            logger.debug("Showing config")
            show_all_config()
        elif inp in ["2", "edit"]:
            logger.debug("Editing config")
            from .editor import edit_config

            edit_config()
        elif inp in ["3", "database", "db"]:
            logger.debug("Opening database management menu")
            from .database_menu import database_management_menu

            database_management_menu()
        elif inp in ["4", "exit", "quit", "q"]:
            logger.debug("Exiting config menu")
            return
        else:
            ui.print_error(f"Invalid option: '{inp}'")


def show_all_config() -> None:
    """
    Show all configuration sections.

    Displays formatted tables for each major configuration section
    including server, authentication, packet sniffer, and beacon settings.
    """
    ui = get_ui_manager()
    sections = ["server", "authentication", "packetsniffer", "beacon"]

    for section in sections:
        show_config(section)
        ui.print("")


def show_config(section: str) -> None:
    """
    Display configuration for a specific section.

    Args:
        section: Name of the configuration section to display
    """
    ui = get_ui_manager()
    config = loadedConfig.get(section, {})
    logger.debug(f"Showing config for {section}: {config}")

    if not config:
        ui.print_warning(f"No configuration found for '{section}'")
        return

    ui.console.print(create_config_table(section, config))
