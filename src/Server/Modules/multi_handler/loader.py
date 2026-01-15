# ============================================================================
# Multi Handler Loader Module
# ============================================================================
# This module handles loading implants (beacons and sessions) from the database
# into memory for persistence across server restarts.
# ============================================================================

# Standard Library Imports
import ast

from ..beacon.beacon import add_beacon_list

# Local Module Imports
from ..global_objects import config, logger


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
            # Note: Sessions require active SSL connections and cannot be
            # restored from database. They are persisted only for historical
            # logging purposes. Unlike beacons which can reconnect via HTTP,
            # sessions maintain live socket connections that don't persist
            # across server restarts.
            logger.debug(
                "Skipping session restoration from database "
                "(sessions require active connections)"
            )

        except Exception as e:
            logger.error(f"Failed to load implants from DB: {e}")
