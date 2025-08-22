"""
Global Objects that are allowed to be accessed anywhere within the project.
This allows for a single form of management with items such as
connected sockets and the ability alter them.

Contains error-handled send and receive functions that
can handle bytes and strings.
"""

from .utils.content_handler import TomlFiles
from .utils.logging import LoggingClass as Logger
from tomlkit.exceptions import InvalidCharInStringError

import os
import sys


beacon_list = {}
command_list = {}
sessions_list = {}
multiplayer_connections = {}

if getattr(sys, "frozen", False):
    base_dir = os.path.expanduser("~/.PrometheanProxy")
    plugin_dir = os.path.join(base_dir, "Plugins")
    config_dir = base_dir
else:
    # Running from source: use repository's Server/Plugins and Server/config.toml
    server_root = os.path.dirname(os.path.dirname(__file__))  # .../src/Server
    plugin_dir = os.path.join(server_root, "Plugins")
    # Use local config at src/Server/config.toml when running as a script
    config_dir = server_root

# Ensure directory exists (no-op for most executable directories if not writable)
try:
    os.makedirs(config_dir, exist_ok=True)
except PermissionError:
    # If we can't create the directory next to the exe, fall back to home dir
    if getattr(sys, "frozen", False):
        config_dir = os.path.expanduser("~/.PrometheanProxy/")
        os.makedirs(config_dir, exist_ok=True)

config_file_path = os.path.join(config_dir, "config.toml")

try:
    with TomlFiles(config_file_path) as f:
        config = f
except FileNotFoundError:
    with TomlFiles(config_file_path) as f:
        config = f
except InvalidCharInStringError:
    os.remove(config_file_path)
    print("Invalid character found in config file. Regenerating config file.")
    with TomlFiles(config_file_path) as f:
        config = f

logger = Logger(
    name="Server",
    log_file=os.path.join(config_dir, config["logging"]["log_file"]),
    level=config["logging"]["level"],
    fmt=config["logging"]["fmt"],
    datefmt=config["logging"]["datefmt"],
    max_size=config["logging"]["max_size"]
)


def execute_local_commands(value: str) -> bool:
    """
    Executes local commands on the server side.
    """
    if value.lower().startswith(
        ("ls", "cat", "pwd", "ping", "curl", "whoami", "\\", "clear")
    ):
        if value.startswith("\\"):
            value = value.replace("\\", "")
        logger.debug(f"Executing local command: {value}")
        os.system(value)
        return True
    else:
        return False


def tab_completion(text: str, state: int, variables: list) -> str:
    """
    Allows for tab completion in the config menu.
    """
    options = [var for var in variables if var.startswith(text)]
    return options[state] if state < len(options) else None
