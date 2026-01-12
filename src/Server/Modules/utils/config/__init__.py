"""
Config Module - Configuration Management

This module provides configuration management for PrometheanProxy.

Main Components:
    - config_menu: Main configuration menu entry point
    - edit_config: Configuration value editor
    - beacon_config_menu: Beacon-specific configuration
    - database_management_menu: Database management functions

Usage:
    from Modules.utils.config import config_menu

    config_menu()  # Opens the main configuration menu
"""

# Shared utilities
# Beacon configuration
from .beacon_config import (
    beacon_config_menu,
    edit_beacon_config,
    get_beacon_config,
    set_beacon_interval,
    set_beacon_jitter,
)

# Database management
from .database_menu import (
    clear_database,
    clear_specific_table,
    database_management_menu,
    get_persistence_status,
    list_all_tables,
    set_persistence,
    show_database_config,
    toggle_persistence,
)

# Config editor
from .editor import edit_config, edit_single_value

# Main menu
from .menu import config_menu, show_all_config, show_config
from .shared import CONFIG_FILE_PATH, create_completer, get_prompt_session

__all__ = [
    # Shared
    "CONFIG_FILE_PATH",
    "get_prompt_session",
    "create_completer",
    # Main menu
    "config_menu",
    "show_all_config",
    "show_config",
    # Editor
    "edit_config",
    "edit_single_value",
    # Beacon config
    "beacon_config_menu",
    "edit_beacon_config",
    "get_beacon_config",
    "set_beacon_interval",
    "set_beacon_jitter",
    # Database menu
    "database_management_menu",
    "show_database_config",
    "clear_database",
    "clear_specific_table",
    "list_all_tables",
    "toggle_persistence",
    "get_persistence_status",
    "set_persistence",
]
