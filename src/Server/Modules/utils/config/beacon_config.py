"""
Beacon Config Module - Beacon-Specific Configuration

Provides functions for viewing and editing beacon configuration
settings such as interval and jitter.
"""

from prompt_toolkit.completion import WordCompleter

from ...global_objects import config as loadedConfig
from ...global_objects import logger
from ..content_handler import TomlFiles
from ..ui import create_menu_table, get_ui_manager
from .shared import CONFIG_FILE_PATH, get_prompt_session


def beacon_config_menu() -> None:
    """
    Beacon configuration menu with modern UI.

    Provides options to view and edit beacon-specific settings
    like callback interval and jitter.
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()

    menu_options = {
        "1": "Show Beacon Config",
        "2": "Edit Beacon Config",
        "3": "Exit Menu",
    }

    completer = WordCompleter(["1", "2", "3", "show", "edit", "exit", "quit", "q"])

    while True:
        logger.debug("Beacon config menu started")
        ui.print("")
        ui.console.print(create_menu_table("Beacon Configuration", menu_options))
        ui.print("")

        try:
            inp = (
                prompt_session.prompt(
                    "Beacon Config ❯ ",
                    completer=completer,
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            return

        if inp in ["1", "show"]:
            logger.debug("Showing beacon config")
            from .menu import show_config

            show_config("beacon")
        elif inp in ["2", "edit"]:
            logger.debug("Editing beacon config")
            edit_beacon_config()
        elif inp in ["3", "exit", "quit", "q"]:
            logger.debug("Exiting beacon config menu")
            return
        else:
            ui.print_error(f"Invalid option: '{inp}'")


def edit_beacon_config() -> None:
    """
    Edit beacon configuration with modern prompts.

    Allows editing of beacon interval and jitter settings
    with validation and help text.
    """
    ui = get_ui_manager()
    prompt_session = get_prompt_session()
    logger.debug("Editing beacon config")

    beacon_keys = ["interval", "jitter"]
    completer = WordCompleter(beacon_keys + ["cancel"])

    # Show current config
    from .menu import show_config

    show_config("beacon")

    ui.print("")
    ui.print("[dim]Note: Times are in seconds. Changes only affect new beacons.[/]")
    ui.print("[dim]Edit live beacons through the beacon interaction menu.[/]")
    ui.print("")

    try:
        key = (
            prompt_session.prompt(
                "Setting to edit (or 'cancel') ❯ ",
                completer=completer,
            )
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        return

    if key == "cancel":
        ui.print_info("Cancelled")
        return

    if key not in beacon_keys:
        ui.print_error(f"Invalid setting: '{key}'")
        return

    current_value = loadedConfig.get("beacon", {}).get(key)
    ui.print(f"\n[dim]Current value:[/] [bright_cyan]{current_value}[/]")

    # Show help for specific settings
    if key == "interval":
        ui.print("[dim]Interval: Time between beacon callbacks (in seconds)[/]")
    elif key == "jitter":
        ui.print("[dim]Jitter: Random variance added to interval (in seconds)[/]")

    try:
        new_value = prompt_session.prompt("New value ❯ ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not new_value:
        ui.print_info("No value entered, cancelled")
        return

    # Validate numeric input
    validated_value = _validate_beacon_value(new_value, key, ui)
    if validated_value is None:
        return

    # Update in-memory config
    if "beacon" not in loadedConfig:
        loadedConfig["beacon"] = {}
    loadedConfig["beacon"][key] = validated_value
    logger.info(f"Updated beacon.{key} to {validated_value}")

    # Update config file
    try:
        toml_file = TomlFiles(CONFIG_FILE_PATH)
        toml_file.update_config("beacon", key, validated_value)
        ui.print_success(f"Updated beacon.{key} = {validated_value}")
    except Exception as e:
        logger.error(f"Failed to save beacon config: {e}")
        ui.print_error(f"Failed to save config: {e}")


def _validate_beacon_value(value: str, key: str, ui):
    """
    Validate a beacon configuration value.

    Args:
        value: The value to validate as a string
        key: The configuration key name
        ui: UIManager instance for output

    Returns:
        Validated value (int or float) or None if invalid
    """
    try:
        # Try parsing as float first (for jitter which might be fractional)
        if "." in value:
            num_value = float(value)
        else:
            num_value = int(value)

        if num_value < 0:
            ui.print_error("Value must be positive")
            return None

        # Specific validation for interval
        if key == "interval":
            if num_value < 1:
                ui.print_warning("Very short intervals may cause high network traffic")
            if num_value > 86400:  # 24 hours
                ui.print_warning("Very long intervals may affect responsiveness")

        # Specific validation for jitter
        if key == "jitter":
            interval = loadedConfig.get("beacon", {}).get("interval", 10)
            if num_value > interval:
                ui.print_warning(
                    f"Jitter ({num_value}s) is larger than interval ({interval}s)"
                )

        return num_value

    except ValueError:
        ui.print_error("Invalid value. Please enter a number.")
        return None


def get_beacon_config() -> dict:
    """
    Get the current beacon configuration.

    Returns:
        Dictionary with beacon configuration values
    """
    return loadedConfig.get("beacon", {"interval": 10, "jitter": 2})


def set_beacon_interval(interval: int) -> bool:
    """
    Set the beacon callback interval.

    Args:
        interval: Interval in seconds

    Returns:
        bool: True if successful
    """
    if interval < 0:
        return False

    if "beacon" not in loadedConfig:
        loadedConfig["beacon"] = {}
    loadedConfig["beacon"]["interval"] = interval

    try:
        toml_file = TomlFiles(CONFIG_FILE_PATH)
        toml_file.update_config("beacon", "interval", interval)
        logger.info(f"Set beacon interval to {interval}")
        return True
    except Exception as e:
        logger.error(f"Failed to set beacon interval: {e}")
        return False


def set_beacon_jitter(jitter: int) -> bool:
    """
    Set the beacon callback jitter.

    Args:
        jitter: Jitter in seconds

    Returns:
        bool: True if successful
    """
    if jitter < 0:
        return False

    if "beacon" not in loadedConfig:
        loadedConfig["beacon"] = {}
    loadedConfig["beacon"]["jitter"] = jitter

    try:
        toml_file = TomlFiles(CONFIG_FILE_PATH)
        toml_file.update_config("beacon", "jitter", jitter)
        logger.info(f"Set beacon jitter to {jitter}")
        return True
    except Exception as e:
        logger.error(f"Failed to set beacon jitter: {e}")
        return False
