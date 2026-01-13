# ============================================================================
# Multi Handler Commands Module
# ============================================================================
# This module provides command handling for the multi-handler interface,
# managing interactions with sessions, beacons, and plugins.
# ============================================================================

# Standard Library Imports
import importlib
import inspect
import os
import pkgutil
import sys
from types import SimpleNamespace

# Third-Party Imports
import colorama

# Local Module Imports
from ServerDatabase.database import DatabaseClass

from ..global_objects import logger

# Import command handler classes
from .command_handlers.connection_handler import ConnectionHandler
from .command_handlers.database_handler import DatabaseHandler
from .command_handlers.interaction_handler import InteractionHandler
from .command_handlers.utility_handler import UtilityHandler

# ============================================================================
# MultiHandlerCommands Class
# ============================================================================


class MultiHandlerCommands(
    ConnectionHandler, InteractionHandler, DatabaseHandler, UtilityHandler
):
    """
    Main command handler for the multi-handler module.

    Inherits from specialized command handler classes to provide a comprehensive
    set of commands for managing sessions, beacons, database operations, and
    utility functions. Also handles dynamic plugin loading and execution.

    Attributes:
        config: Server configuration dictionary
        database: Database connection instance
        session_plugins: Dictionary mapping command names to session plugin instances
        beacon_plugins: Dictionary mapping command names to beacon plugin instances
    """

    def __init__(self, config, prompt_session) -> None:
        """Initialize the command handler with configuration and load plugins."""
        logger.info("Initializing MultiHandlerCommands")
        self.config = config
        self.prompt_session = prompt_session
        self.database = DatabaseClass(config, "command_database")
        colorama.init(autoreset=True)

        self._plugins_loaded = False
        self.session_plugins = {}  # command -> instance
        self.beacon_plugins = {}  # command -> instance

        try:
            self.load_plugins()
        except Exception as e:
            logger.exception(f"Failed to load Plugins: {e}")
        return

    # ========================================================================
    # Plugin Loading and Management
    # ========================================================================

    # ========================================================================
    # Plugin Loading and Management
    # ========================================================================

    def load_plugins(self, package_name: str = "Plugins") -> None:
        """
        Discover and load plugin classes from the Plugins package.

        Searches for plugin classes that implement session() or beacon() methods
        and instantiates them for later execution. Supports both development
        (source) and packaged (PyInstaller) environments.

        A plugin is any class that defines:
        - session(self, session: dict): Handler for session commands
        - beacon(self, beacon): Handler for beacon commands
        - command (optional): String attribute specifying command name

        Args:
            package_name: Root package name to search for plugins (default: "Plugins")
        """
        import os
        import sys

        # ----------------------------------------------------------------
        # Determine Plugin Path (Dev vs Packaged Binary)
        # ----------------------------------------------------------------
        # When running as a packaged binary (PyInstaller), prefer user plugins
        # extracted to ~/.PrometheanProxy/plugins (contains top-level 'Plugins/' dir).
        user_plugins_root = os.path.expanduser("~/.PrometheanProxy/plugins")
        packaged = getattr(sys, "_MEIPASS", None) is not None

        if packaged and os.path.isdir(os.path.join(user_plugins_root, "Plugins")):
            # Prepend so 'import Plugins' resolves to user plugin folder first
            if user_plugins_root not in sys.path:
                sys.path.insert(0, user_plugins_root)
        else:
            # Dev/source mode: ensure the Server root (src/Server) is on sys.path
            this_dir = os.path.dirname(__file__)
            server_dir = os.path.abspath(
                os.path.join(this_dir, "..", "..")
            )  # .../src/Server
            if server_dir not in sys.path:
                sys.path.insert(0, server_dir)

            # Optionally also include project src
            project_src = os.path.abspath(os.path.join(server_dir, ".."))  # .../src
            if project_src not in sys.path:
                sys.path.append(project_src)

        # ----------------------------------------------------------------
        # Search for Plugin Modules
        # ----------------------------------------------------------------
        # Try both top-level package ("Plugins") and namespaced ("Server.Plugins").
        packages_to_try = [package_name]
        if package_name != "Server.Plugins":
            packages_to_try.append("Server.Plugins")
        discovered = 0

        for pkg_name in packages_to_try:
            try:
                pkg = importlib.import_module(pkg_name)
            except Exception as e:
                logger.info(f"Plugin package '{pkg_name}' not importable: {e}")
                continue

            # Walk through all modules in the package
            for _, mod_name, _ in pkgutil.walk_packages(
                pkg.__path__, pkg.__name__ + "."
            ):
                try:
                    mod = importlib.import_module(mod_name)
                except Exception as e:
                    logger.error(f"Failed to import plugin module {mod_name}: {e}")
                    continue

                # --------------------------------------------------------
                # Inspect Module for Plugin Classes
                # --------------------------------------------------------
                for _, cls in inspect.getmembers(mod, inspect.isclass):
                    # Skip classes not defined in this module
                    if cls.__module__ != mod.__name__:
                        continue

                    # Check if class has required plugin methods
                    has_session = callable(getattr(cls, "session", None))
                    has_beacon = callable(getattr(cls, "beacon", None))
                    if not (has_session or has_beacon):
                        continue

                    # Instantiate plugin class
                    try:
                        instance = cls()
                    except Exception as e:
                        logger.error(
                            f"Failed to instantiate plugin "
                            f"{mod_name}.{cls.__name__}: {e}"
                        )
                        continue

                    # Use 'command' attribute as key, or fall back to class name
                    key = getattr(instance, "command", None) or cls.__name__

                    # Register plugin (avoid overwriting already loaded plugins)
                    if has_session and key not in self.session_plugins:
                        self.session_plugins[key] = instance
                    if has_beacon and key not in self.beacon_plugins:
                        self.beacon_plugins[key] = instance

                    discovered += 1
                    logger.debug(
                        f"Loaded plugin {mod_name}.{cls.__name__} as key '{key}' "
                        f"(session={has_session}, beacon={has_beacon})"
                    )

        self._plugins_loaded = True
        logger.info(
            f"Plugins loaded: session={len(self.session_plugins)}, "
            f"beacon={len(self.beacon_plugins)} (classes scanned={discovered})"
        )

    def list_loaded_session_commands(self):
        """
        List all loaded session plugin commands.

        Returns:
            list: Sorted list of session command names
        """
        self.load_plugins()
        return sorted(self.session_plugins.keys())

    def list_loaded_beacon_commands(self):
        """
        List all loaded beacon plugin commands.

        Returns:
            list: Sorted list of beacon command names
        """
        self.load_plugins()
        return sorted(self.beacon_plugins.keys())

    # ========================================================================
    # Plugin Execution Methods
    # ========================================================================

    # ========================================================================
    # Plugin Execution Methods
    # ========================================================================

    def run_session_plugin(
        self, command: str, conn, r_address, user_id: str | None = None
    ) -> None:
        """
        Execute a session plugin command.

        Invokes the session() method on the named plugin with the provided
        connection details.

        Args:
            command: Name of the session plugin command to run
            conn: SSL socket connection object to the session
            r_address: Remote address tuple (host, port) of the session
            user_id: Unique identifier for the session (optional)
        """
        self.load_plugins()
        plugin = self.session_plugins.get(command)
        if not plugin:
            logger.error(f"Session plugin '{command}' not found.")
            return

        # Provide the shape expected by plugins: {'userID': str, 'conn': sslSocket}
        session = {"userID": user_id or r_address[0], "conn": conn}
        try:
            # Call init method if it exists
            if hasattr(plugin, "init"):
                plugin.init(session)

            logger.info(f"Running session plugin '{command}' for {session['userID']}")
            plugin.session(session)
        except Exception as e:
            logger.error(f"Session plugin '{command}' failed: {e}")

    def run_beacon_plugin(self, command: str, userID: str) -> bool:
        """
        Execute a beacon plugin command.

        Invokes the beacon() method on the named plugin with the provided
        beacon ID. If the plugin is not pre-loaded, attempts to dynamically
        import it using fallback conventions.

        Args:
            command: Name of the beacon plugin command to run
            userID: Unique identifier for the beacon

        Returns:
            bool: True if plugin was found and executed, False otherwise
        """
        self.load_plugins()
        plugin = self.beacon_plugins.get(command)

        if not plugin:
            # --------------------------------------------------------
            # Fallback: Dynamic Import by Convention
            # --------------------------------------------------------
            import importlib
            import inspect

            tried = []

            # Use correct-cased package names
            for base in ("Plugins", "Server.Plugins"):
                for mod_name in (f"{base}.{command}.{command}", f"{base}.{command}"):
                    try:
                        tried.append(mod_name)
                        mod = importlib.import_module(mod_name)

                        # Find a class with a beacon method
                        for _, cls in inspect.getmembers(mod, inspect.isclass):
                            if cls.__module__ != mod.__name__:
                                continue
                            if callable(getattr(cls, "beacon", None)):
                                try:
                                    instance = cls()
                                    key = (
                                        getattr(instance, "command", None)
                                        or cls.__name__
                                    )
                                    # Store for next time if key matches requested
                                    self.beacon_plugins[key] = instance
                                    plugin = instance if key == command else None
                                    logger.info(
                                        f"Dynamically imported plugin '{mod_name}' "
                                        f"as key '{key}'"
                                    )
                                    break
                                except Exception as e:
                                    logger.error(
                                        f"Failed to instantiate fallback plugin "
                                        f"{mod_name}.{cls.__name__}: {e}"
                                    )
                                    continue
                        if plugin:
                            break
                    except Exception as e:
                        logger.debug(f"Fallback import failed for {mod_name}: {e}")
                if plugin:
                    break

            if not plugin:
                logger.error(
                    f"Beacon plugin '{command}' not found after trying: "
                    f"{', '.join(tried) if tried else 'no modules'}."
                )
                return False

        # Execute plugin
        beacon_like = SimpleNamespace(userID=userID)
        try:
            # Call init method if it exists
            if hasattr(plugin, "init"):
                plugin.init(beacon_like)

            logger.info(f"Queueing beacon plugin '{command}' for {userID}")
            plugin.beacon(beacon_like)
            return True
        except Exception as e:
            logger.error(f"Beacon plugin '{command}' failed: {e}")
            return False
