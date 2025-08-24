from ServerDatabase.database import DatabaseClass
from ..global_objects import logger

# Plugin discovery
import importlib
import inspect
import pkgutil
from types import SimpleNamespace

# Import the new component handler classes
from .command_handlers.connection_handler import ConnectionHandler
from .command_handlers.interaction_handler import InteractionHandler
from .command_handlers.database_handler import DatabaseHandler
from .command_handlers.utility_handler import UtilityHandler

import colorama


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
        self._plugins_loaded = False
        self.session_plugins = {}  # command -> instance
        self.beacon_plugins = {}   # command -> instance
        try:
            self.load_plugins()
        except Exception as e:
            logger.exception(f"Failed to load Plugins: {e}")
        return

    def load_plugins(self, package_name: str = "Plugins") -> None:
        """Discover and instantiate plugin classes under Plugins/.

        A plugin is any class in a module under package_name that defines
        at least one of: session(self, session: dict), beacon(self, beacon)
        and (optionally) a 'command' attribute. If 'command' is missing,
        the class name is used as the key.
        """
    # Allow re-discovery to pick up newly added plugins or recover after
    # an initial import failure. We'll still avoid duplicate keys below.
    # Set a soft guard to prevent infinite recursion.
    # Callers may invoke load_plugins() multiple times; that's fine.

        import os, sys
        # When running as a packaged binary (PyInstaller), prefer user plugins
        # extracted to ~/.PrometheanProxy/plugins (contains top-level 'Plugins/' dir).
        user_plugins_root = os.path.expanduser('~/.PrometheanProxy/plugins')
        packaged = getattr(sys, '_MEIPASS', None) is not None
        if packaged and os.path.isdir(os.path.join(user_plugins_root, 'Plugins')):
            # Prepend so 'import Plugins' resolves to user plugin folder first
            if user_plugins_root not in sys.path:
                sys.path.insert(0, user_plugins_root)
        else:
            # Dev/source mode: ensure the Server root (src/Server) is on sys.path
            this_dir = os.path.dirname(__file__)
            server_dir = os.path.abspath(os.path.join(this_dir, "..", ".."))  # .../src/Server
            if server_dir not in sys.path:
                sys.path.insert(0, server_dir)
            # Optionally also include project src
            project_src = os.path.abspath(os.path.join(server_dir, ".."))  # .../src
            if project_src not in sys.path:
                sys.path.append(project_src)

        # Try both top-level package ("Plugins") and namespaced ("Server.Plugins").
        # Note: Correct casing matters on Linux; avoid lower-case variants.
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

            for _, mod_name, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                try:
                    mod = importlib.import_module(mod_name)
                except Exception as e:
                    logger.error(f"Failed to import plugin module {mod_name}: {e}")
                    continue

                for _, cls in inspect.getmembers(mod, inspect.isclass):
                    if cls.__module__ != mod.__name__:
                        continue
                    has_session = callable(getattr(cls, "session", None))
                    has_beacon = callable(getattr(cls, "beacon", None))
                    if not (has_session or has_beacon):
                        continue
                    try:
                        instance = cls()
                    except Exception as e:
                        logger.error(f"Failed to instantiate plugin {mod_name}.{cls.__name__}: {e}")
                        continue
                    key = getattr(instance, "command", None) or cls.__name__
                    # Avoid overwriting already loaded plugins from another package path
                    if has_session and key not in self.session_plugins:
                        self.session_plugins[key] = instance
                    if has_beacon and key not in self.beacon_plugins:
                        self.beacon_plugins[key] = instance
                    discovered += 1
                    logger.debug(f"Loaded plugin {mod_name}.{cls.__name__} as key '{key}' (session={has_session}, beacon={has_beacon})")

        self._plugins_loaded = True
        logger.info(
            f"Plugins loaded: session={len(self.session_plugins)}, "
            f"beacon={len(self.beacon_plugins)} (classes scanned={discovered})"
        )

    def list_loaded_session_commands(self):
        self.load_plugins()
        return sorted(self.session_plugins.keys())

    def list_loaded_beacon_commands(self):
        self.load_plugins()
        return sorted(self.beacon_plugins.keys())

    def run_session_plugin(self, command: str, conn, r_address, user_id: str | None = None) -> None:
        """Invoke session(session_dict) on the named plugin, if present."""
        self.load_plugins()
        plugin = self.session_plugins.get(command)
        if not plugin:
            logger.error(f"Session plugin '{command}' not found.")
            return
        # Provide the shape used by plugins: {'userID': str, 'conn': sslSocket}
        session = {"userID": user_id or r_address[0], "conn": conn}
        try:
            logger.info(f"Running session plugin '{command}' for {session['userID']}")
            plugin.session(session)
        except Exception as e:
            logger.error(f"Session plugin '{command}' failed: {e}")

    def run_beacon_plugin(self, command: str, userID: str) -> bool:
        """Invoke beacon(beacon_like) on the named plugin, if present.

        We pass a simple object exposing .userID to satisfy plugins that
        expect that attribute.
        """
        self.load_plugins()
        plugin = self.beacon_plugins.get(command)
        if not plugin:
            # Fallback: attempt to import by convention
            import importlib, inspect
            tried = []
            # Use correct-cased package names
            for base in ("Plugins", "Server.Plugins"):
                for mod_name in (f"{base}.{command}.{command}", f"{base}.{command}"):
                    try:
                        tried.append(mod_name)
                        mod = importlib.import_module(mod_name)
                        # find a class with a beacon method
                        for _, cls in inspect.getmembers(mod, inspect.isclass):
                            if cls.__module__ != mod.__name__:
                                continue
                            if callable(getattr(cls, "beacon", None)):
                                try:
                                    instance = cls()
                                    key = getattr(instance, "command", None) or cls.__name__
                                    # store for next time if key matches requested
                                    self.beacon_plugins[key] = instance
                                    plugin = instance if key == command else None
                                    logger.info(f"Dynamically imported plugin '{mod_name}' as key '{key}'")
                                    break
                                except Exception as e:
                                    logger.error(f"Failed to instantiate fallback plugin {mod_name}.{cls.__name__}: {e}")
                                    continue
                        if plugin:
                            break
                    except Exception as e:
                        logger.debug(f"Fallback import failed for {mod_name}: {e}")
                if plugin:
                    break
            if not plugin:
                logger.error(f"Beacon plugin '{command}' not found after trying: {', '.join(tried) if tried else 'no modules'}.")
                return False
        
        beacon_like = SimpleNamespace(userID=userID)
        try:
            logger.info(f"Queueing beacon plugin '{command}' for {userID}")
            plugin.beacon(beacon_like)
            return True
        except Exception as e:
            logger.error(f"Beacon plugin '{command}' failed: {e}")
            return False