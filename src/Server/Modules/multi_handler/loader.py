# ============================================================================
# Multi Handler Loader Module
# ============================================================================
# This module handles loading implants (beacons and sessions) from the database
# into memory for persistence across server restarts.
# ============================================================================

# Standard Library Imports
import ast
import uuid

from ..beacon.beacon import add_beacon_list

# Local Module Imports
from ..global_objects import config, logger
from ..session.session import add_connection_list


class LoaderMixin:
    """
    Mixin class providing database loading functionality.

    This mixin provides methods for loading stored implants (beacons and
    sessions) from the database back into memory when the server starts.
    """

    def load_db_implants(self) -> None:
        """
        Load implants from the database into memory.

        Retrieves stored beacons and sessions from the database and recreates
        them in the active connection lists. This allows persistence of
        connections across server restarts.
        """
        logger.info("Loading implants from database")
        try:
            # ----------------------------------------------------------------
            # Load Beacons from Database
            # ----------------------------------------------------------------
            # Schema: uuid, IP, Hostname, OS, LastBeacon, NextBeacon,
            #         Timer, Jitter, modules
            beacons = self.database.fetch_all("beacons")
            if beacons:
                for beacon in beacons:
                    try:
                        # Parse beacon data from database row
                        uuid_val = beacon[0]
                        ip = beacon[1]
                        hostname = beacon[2]
                        os_val = beacon[3]

                        # Handle last_beacon time conversion
                        try:
                            last_beacon = beacon[4]
                        except (ValueError, TypeError):
                            last_beacon = float(beacon[4]) if beacon[4] else 0.0

                        # Parse timing information
                        timer = float(beacon[6]) if beacon[6] else 0.0
                        jitter = float(beacon[7]) if beacon[7] else 0.0

                        # Parse modules list
                        modules_data = beacon[8]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = (
                                modules_data if isinstance(modules_data, list) else []
                            )

                        # Add beacon to active list
                        add_beacon_list(
                            uuid_val,
                            ip,
                            hostname,
                            os_val,
                            last_beacon,
                            timer,
                            jitter,
                            config,
                            self.database,
                            modules,
                            from_db=True,
                        )
                        logger.debug(f"Loaded beacon from DB: {uuid_val}")
                    except Exception as e:
                        logger.error(f"Error loading beacon {beacon}: {e}")
                        continue

                logger.info(f"Loaded {len(beacons)} beacons from database")

            # ----------------------------------------------------------------
            # Load Sessions from Database
            # ----------------------------------------------------------------
            # Schema: address, details, hostname, operating_system,
            #         mode, modules
            sessions = self.database.fetch_all("sessions")
            if sessions:
                for session in sessions:
                    try:
                        # Parse address data
                        address_data = session[0]
                        if isinstance(address_data, str):
                            try:
                                address = ast.literal_eval(address_data)
                            except (ValueError, SyntaxError):
                                address = (address_data, 0)
                        else:
                            address = address_data

                        # Parse session details
                        details = session[1]
                        hostname = session[2]
                        operating_system = session[3]
                        mode = session[4]

                        # Parse modules list
                        modules_data = session[5]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = (
                                modules_data if isinstance(modules_data, list) else []
                            )

                        # Generate user ID for session
                        user_id = str(uuid.uuid4())

                        # Add session to active list
                        add_connection_list(
                            details,
                            address,
                            hostname,
                            operating_system,
                            user_id,
                            mode,
                            modules,
                            config,
                            from_db=True,
                        )
                        logger.debug(f"Loaded session from DB: {hostname}")
                    except Exception as e:
                        logger.error(f"Error loading session {session}: {e}")
                        continue

                logger.info(f"Loaded {len(sessions)} sessions from database")

        except Exception as e:
            logger.error(f"Failed to load implants from DB: {e}")
