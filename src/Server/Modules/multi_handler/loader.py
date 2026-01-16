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
            # Load Connections from Unified Database Table
            # ----------------------------------------------------------------
            # Schema: uuid, ip, hostname, os, connection_type, last_seen,
            #         next_beacon, timer, jitter, modules, session_address,
            #         last_mode_switch, created_at
            connections = self.database.fetch_all("connections")
            if connections:
                beacons_loaded = 0
                for connection in connections:
                    try:
                        # Parse connection data from database row
                        uuid_val = connection[0]
                        ip = connection[1]
                        hostname = connection[2]
                        os_val = connection[3]
                        connection_type = connection[4]
                        last_seen = connection[5]
                        next_beacon = connection[6]
                        timer = connection[7]
                        jitter = connection[8]
                        modules_data = connection[9]
                        # session_address = connection[10]  # Not used for beacons
                        # last_mode_switch = connection[11]  # Future use
                        # created_at = connection[12]  # Future use

                        # Only load beacons - sessions require active connections
                        if connection_type != "beacon":
                            logger.debug(
                                f"Skipping {connection_type} {uuid_val} "
                                "(sessions require active connections)"
                            )
                            continue

                        # Handle last_seen time conversion
                        try:
                            last_beacon = float(last_seen) if last_seen else 0.0
                        except (ValueError, TypeError):
                            last_beacon = 0.0

                        # Parse timing information
                        timer_val = float(timer) if timer else 0.0
                        jitter_val = float(jitter) if jitter else 0.0

                        # Parse modules list with robust type checking
                        if isinstance(modules_data, str):
                            try:
                                parsed = ast.literal_eval(modules_data)
                                # Ensure parsed result is a list
                                if isinstance(parsed, list):
                                    modules = parsed
                                else:
                                    logger.warning(
                                        f"Parsed modules is not a list for beacon {uuid_val} "
                                        f"(got {type(parsed).__name__}): {modules_data}. "
                                        "Defaulting to empty list."
                                    )
                                    modules = []
                            except (ValueError, SyntaxError):
                                logger.warning(
                                    f"Failed to parse modules string for beacon {uuid_val}: "
                                    f"{modules_data}. Defaulting to empty list."
                                )
                                modules = []
                        elif isinstance(modules_data, list):
                            modules = modules_data
                        else:
                            # Handle any other type (bool, None, int, etc.)
                            logger.warning(
                                f"Invalid modules type for beacon {uuid_val} "
                                f"({type(modules_data).__name__}): {modules_data}. "
                                "Defaulting to empty list."
                            )
                            modules = []

                        # Add beacon to active list
                        add_beacon_list(
                            uuid_val,
                            ip,
                            hostname,
                            os_val,
                            last_beacon,
                            timer_val,
                            jitter_val,
                            config,
                            self.database,
                            modules,
                            from_db=True,
                        )
                        logger.debug(f"Loaded beacon from DB: {uuid_val}")
                        beacons_loaded += 1
                    except Exception as e:
                        logger.error(f"Error loading connection {connection}: {e}")
                        continue

                logger.info(f"Loaded {beacons_loaded} beacons from database")

        except Exception as e:
            logger.error(f"Failed to load implants from DB: {e}")
