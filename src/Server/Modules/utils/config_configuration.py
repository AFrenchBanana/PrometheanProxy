"""
Configuration Management Module - Backwards Compatibility Wrapper

This module re-exports all configuration components from the new modular
config package for backwards compatibility with existing code.

New code should import directly from:
    from Modules.utils.config import config_menu, edit_config, etc.
"""

# Re-export everything from the new config module for backwards compatibility
from .config import (
    # Shared
    CONFIG_FILE_PATH,
    # Beacon config
    beacon_config_menu,
    clear_database,
    clear_specific_table,
    # Main menu
    config_menu,
    create_completer,
    # Database menu
    database_management_menu,
    edit_beacon_config,
    # Editor
    edit_config,
    edit_single_value,
    get_beacon_config,
    get_persistence_status,
    get_prompt_session,
    list_all_tables,
    set_beacon_interval,
    set_beacon_jitter,
    set_persistence,
    show_all_config,
    show_config,
    show_database_config,
    toggle_persistence,
)

# Also import UI components that were previously used here
from .ui import create_config_table, create_menu_table, get_ui_manager

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
    # UI components (for backwards compat)
    "create_menu_table",
    "create_config_table",
    "get_ui_manager",
]
