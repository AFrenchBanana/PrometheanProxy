# Modules/multi_handler/multi_handler_commands.py

"""
multi handler commands. Functions to complete tasks within
the multi handler menu. conn and r_address variables are ,
connection and address variables fed in from the specified socket.
this allows for multiple connections to be interacted with.
"""

from ServerDatabase.database import DatabaseClass
from ..global_objects import logger

# Import the new component handler classes
from .command_handlers.connection_handler import ConnectionHandler
from .command_handlers.interaction_handler import InteractionHandler
from .command_handlers.database_handler import DatabaseHandler
from .command_handlers.utility_handler import UtilityHandler

import colorama

# The main class is now composed of the handler classes via inheritance.
# This keeps the logic separated into different files but available
# under a single `self` context.
class MultiHandlerCommands(
    ConnectionHandler,
    InteractionHandler,
    DatabaseHandler,
    UtilityHandler
):
    """
    Class with multi-handler commands. Each multi-handler instance
    can call this class to get access to all commands.
    It is built from smaller, specialized handler classes.
    """
    def __init__(self, config) -> None:
        """
        Initializes the command handler, setting up config, database,
        and colorama.
        """
        logger.info("Initializing MultiHandlerCommands")
        self.config = config
        self.database = DatabaseClass(config)
        colorama.init(autoreset=True)
        return