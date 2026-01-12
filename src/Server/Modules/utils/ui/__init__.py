"""
UI Module - Terminal Interface Components

This module provides a clean, modern terminal interface for PrometheanProxy.

Main Components:
    - UIManager: Singleton manager for terminal output
    - Event: Event tracking and display
    - Tables: Styled Rich table factories
    - Theme: Color and style configuration
    - Helpers: Utility functions and classes

Usage:
    from Modules.utils.ui import get_ui_manager, RichPrint

    ui = get_ui_manager()
    ui.print_success("Operation completed!")
"""

# Core manager and singleton accessor
# Event classes
from .events import Event, EventFactory

# Helper classes and functions
from .helpers import (
    Capture,
    RichPrint,
    colorize_bool,
    colorize_status,
    format_bytes,
    format_duration,
    format_ip_address,
    format_uuid,
    truncate_string,
)
from .manager import (
    UIManager,
    get_ui_manager,
    log_beacon_checkin,
    log_beacon_connect,
    log_command,
    log_connection_event,
    log_disconnect,
    log_session_connect,
    update_connection_stats,
)

# Table creation functions
from .tables import (
    create_beacons_table,
    create_command_history_table,
    create_config_table,
    create_database_config_table,
    create_help_table,
    create_menu_table,
    create_multiplayer_table,
    create_sessions_table,
    create_status_table,
    create_tables_list_table,
    create_users_table,
)

# Theme configuration
from .theme import (
    EVENT_STYLES,
    PROMETHEAN_THEME,
    STATUS_INDICATORS,
    TABLE_STYLES,
)

__all__ = [
    # Manager
    "UIManager",
    "get_ui_manager",
    # Convenience logging functions
    "log_connection_event",
    "update_connection_stats",
    "log_session_connect",
    "log_beacon_connect",
    "log_beacon_checkin",
    "log_command",
    "log_disconnect",
    # Events
    "Event",
    "EventFactory",
    # Tables
    "create_sessions_table",
    "create_beacons_table",
    "create_users_table",
    "create_status_table",
    "create_help_table",
    "create_command_history_table",
    "create_menu_table",
    "create_config_table",
    "create_database_config_table",
    "create_tables_list_table",
    "create_multiplayer_table",
    # Theme
    "PROMETHEAN_THEME",
    "EVENT_STYLES",
    "TABLE_STYLES",
    "STATUS_INDICATORS",
    # Helpers
    "Capture",
    "RichPrint",
    "format_bytes",
    "format_duration",
    "truncate_string",
    "format_uuid",
    "format_ip_address",
    "colorize_status",
    "colorize_bool",
]
