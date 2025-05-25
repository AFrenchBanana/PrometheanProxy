"""
Global Objects that are allowed to be accessed anywhere within the project.
This allows for a single form of management with items such as
connected sockets and the ability alter them.

Contains error-handled send and receive functions that
can handle bytes and strings.
"""

from .content_handler import TomlFiles
from .logging import LoggingClass as Logger
import os

beacon_list = {}
command_list = {}
sessions_list = {}


try:
    with TomlFiles("config.toml") as f:
        config = f
except FileNotFoundError:
    with TomlFiles("src/Server/config.toml") as f:
        config = f

logger = Logger(
    name="Server",
    log_file=config["logging"]["log_file"],
    level=config["logging"]["level"],
    fmt=config["logging"]["fmt"],
    datefmt=config["logging"]["datefmt"]
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
