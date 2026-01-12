"""
Config Editor Module - Configuration Value Editing

Provides functions for editing server configuration values
with validation and type checking.
"""

import ipaddress

from prompt_toolkit.completion import WordCompleter
from rich.box import ROUNDED
from rich.table import Table

from ...global_objects import config as loadedConfig
from ...global_objects import logger
from ..content_handler import TomlFiles
from ..ui import get_ui_manager
from .shared import CONFIG_FILE_PATH, get_prompt_session


def edit_config() -> bool:
    """
    Edit configuration with modern prompts.

    Provides an interactive interface for editing server configuration
    values with validation and type checking.

    Returns:
        bool: True if a value was updated, False otherwise
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug("Starting edit config")

    # Define available keys
    main_keys = ["server", "authentication", "packetsniffer", "beacon", "exit"]
    key_options = {
        "server": [
            "listenaddress",
            "port",
            "webPort",
            "TLSCertificateDir",
            "TLSCertificate",
            "TLSkey",
            "GUI",
            "quiet_mode",
            "module_location",
        ],
        "authentication": ["keylength"],
        "packetsniffer": [
            "active",
            "listenaddress",
            "port",
            "TLSCertificate",
            "TLSKey",
            "debugPrint",
        ],
        "beacon": ["interval", "jitter"],
    }

    # Show available sections
    section_table = Table(
        title="[bold bright_yellow]Available Configuration Sections[/]",
        box=ROUNDED,
        border_style="bright_yellow",
        padding=(0, 2),
    )
    section_table.add_column("Section", style="bright_cyan")
    section_table.add_column("Keys", style="dim")

    for section, keys in key_options.items():
        section_table.add_row(
            section, ", ".join(keys[:4]) + ("..." if len(keys) > 4 else "")
        )

    ui.console.print(section_table)
    ui.print("")

    main_completer = WordCompleter(main_keys)

    toml_file = TomlFiles(CONFIG_FILE_PATH)
    with toml_file as config:
        logger.debug("Config file opened for editing")

        while True:
            try:
                key = (
                    prompt_session.prompt(
                        "Section (or 'exit') ❯ ",
                        completer=main_completer,
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                return False

            if key == "exit":
                return False

            if key not in key_options:
                ui.print_error(f"Invalid section: '{key}'")
                continue

            # Show current values for this section
            from .menu import show_config

            show_config(key)

            # Get subkey
            subkey_completer = WordCompleter(key_options[key] + ["back"])

            try:
                subkey = prompt_session.prompt(
                    f"{key} > Setting (or 'back') ❯ ",
                    completer=subkey_completer,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                continue

            if subkey == "back":
                continue

            if subkey not in config.get(key, {}):
                ui.print_error(f"Invalid setting: '{subkey}'")
                continue

            current_value = config[key][subkey]
            current_type = type(current_value).__name__

            ui.print(
                f"\n[dim]Current value:[/] [bright_cyan]{current_value}[/] [dim]({current_type})[/]"
            )

            try:
                new_value = prompt_session.prompt("New value ❯ ").strip()
            except (EOFError, KeyboardInterrupt):
                continue

            # Validate and convert value
            validated_value, is_valid = _validate_value(
                new_value, current_value, subkey, ui
            )

            if is_valid:
                toml_file.update_config(key, subkey, validated_value)
                ui.print_success(f"Updated {key}.{subkey} = {validated_value}")
                ui.print_warning("Restart the server to apply changes")
                logger.info(f"Updated {key}.{subkey} to {validated_value}")
                return True

    return False


def _validate_value(new_value: str, current_value, subkey: str, ui):
    """
    Validate and convert a new configuration value.

    Args:
        new_value: The new value as a string
        current_value: The current value (for type inference)
        subkey: The configuration key name
        ui: UIManager instance for output

    Returns:
        Tuple of (converted_value, is_valid)
    """
    if isinstance(current_value, bool):
        if new_value.lower() in ["true", "yes", "1", "on"]:
            return True, True
        elif new_value.lower() in ["false", "no", "0", "off"]:
            return False, True
        else:
            ui.print_error("Invalid value. Use: true/false, yes/no, 1/0, on/off")
            return None, False

    elif isinstance(current_value, int):
        try:
            int_value = int(new_value)

            # Validate port numbers
            if "port" in subkey.lower():
                if int_value < 1 or int_value > 65535:
                    ui.print_error("Port must be between 1 and 65535")
                    return None, False

            return int_value, True
        except ValueError:
            ui.print_error("Invalid value. Please enter a number.")
            return None, False

    elif isinstance(current_value, float):
        try:
            return float(new_value), True
        except ValueError:
            ui.print_error("Invalid value. Please enter a number.")
            return None, False

    elif subkey == "listenaddress":
        try:
            ipaddress.ip_address(new_value)
            return new_value, True
        except ValueError:
            ui.print_error("Invalid IP address format")
            return None, False

    else:
        # String value - accept as-is
        return new_value, True


def edit_single_value(section: str, key: str, new_value) -> bool:
    """
    Edit a single configuration value programmatically.

    Args:
        section: Configuration section name
        key: Configuration key name
        new_value: New value to set

    Returns:
        bool: True if successful, False otherwise
    """
    logger.debug(f"Editing {section}.{key} to {new_value}")

    try:
        toml_file = TomlFiles(CONFIG_FILE_PATH)
        toml_file.update_config(section, key, new_value)

        # Update in-memory config
        if section in loadedConfig:
            loadedConfig[section][key] = new_value
        else:
            loadedConfig[section] = {key: new_value}

        logger.info(f"Updated {section}.{key} to {new_value}")
        return True
    except Exception as e:
        logger.error(f"Failed to update {section}.{key}: {e}")
        return False
