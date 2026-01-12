# ============================================================================
# Beacon Connection Module
# ============================================================================
# This module provides connection management functionality for beacons,
# including closing connections and session switching.
# ============================================================================

# Standard Library Imports
import traceback

# Third-Party Imports
import colorama

# Local Module Imports
from ..global_objects import logger
from .registry import add_beacon_command_list, remove_beacon_list


class ConnectionMixin:
    """
    Mixin class providing connection management methods for beacons.

    This mixin provides methods for closing beacon connections and
    switching beacons to session mode.
    """

    def close_connection(self, userID: str) -> None:
        """
        Close the beacon connection after user confirmation.

        Queues a shutdown command for the beacon and removes it from the
        active beacon list upon user confirmation.

        Args:
            userID: Unique identifier for the beacon
        """
        confirmation = input(
            colorama.Back.RED + "Are you sure want to close the connection?: y/N "
        )
        if confirmation.lower() == "y":
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + "Closing " + userID)

            try:
                logger.debug(f"Closing connection for beacon: {userID}")
                add_beacon_command_list(userID, None, "shutdown", self.database)

            except BaseException:  # handles ssl.SSLEOFError
                logger.error(f"Error closing connection for beacon: {userID}")
                if not self.config["server"]["quiet_mode"]:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()
                    logger.error(traceback.format_exc())
                pass

            logger.debug(f"Removing beacon from list: {userID}")
            remove_beacon_list(userID)
            print(colorama.Back.GREEN + "Closed")
        else:
            print(colorama.Back.GREEN + "Connection not closed")
        return

    def switch_session(self, userID: str) -> None:
        """
        Switch the beacon to session mode.

        Queues a command instructing the beacon to switch from asynchronous
        beacon mode to persistent session mode.

        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Switching session for userID: {userID}")
        add_beacon_command_list(userID, None, "session", self.database, {})
