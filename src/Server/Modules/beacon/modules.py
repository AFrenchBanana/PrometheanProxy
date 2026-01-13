# ============================================================================
# Beacon Modules Module
# ============================================================================
# This module provides functionality for loading and managing modules on beacons,
# including interactive module selection and direct module loading.
# All modules are sent as interpreted Go source code.
# ============================================================================

# Standard Library Imports
import os
import readline
import traceback

# Local Module Imports
from ..global_objects import logger, obfuscation_map, tab_completion
from .registry import add_beacon_command_list


class ModulesMixin:
    """
    Mixin class providing module loading functionality for beacons.

    This mixin provides methods for discovering available modules,
    loading them interactively or directly, and queuing them as
    commands for beacons to execute. All modules are sent as
    interpreted Go source code.
    """

    def _resolve_module_base(self) -> str:
        """
        Resolve the base directory for modules.

        Prefers unified structure under ~/.PrometheanProxy/plugins but
        falls back to configured module location.

        Returns:
            str: Path to the module base directory
        """
        candidates = [
            os.path.expanduser(self.config["server"].get("module_location", "")),
            os.path.expanduser("~/.PrometheanProxy/plugins"),
        ]
        for c in candidates:
            if c and os.path.isdir(c):
                return c
        # Default to unified location if nothing exists yet
        return os.path.expanduser("~/.PrometheanProxy/plugins")

    def get_available_modules(self) -> list[str]:
        """
        Discover available modules for this beacon's operating system.

        Searches for modules in the plugins directory and filters them
        based on the beacon's operating system.

        Returns:
            list[str]: Sorted list of available module names
        """
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )

        if not os.path.isdir(repo_plugins):
            logger.warning(f"Plugins directory not found: {repo_plugins}")
            return []

        available = []
        for entry in os.listdir(repo_plugins):
            plugin_path = os.path.join(repo_plugins, entry)
            if (
                os.path.isdir(plugin_path)
                and entry != "template"
                and not entry.endswith("__pycache__")
            ):
                # Check if main.go exists
                main_go = os.path.join(plugin_path, "main.go")
                if os.path.exists(main_go):
                    # Check OS compatibility if main.go has GOOS comment
                    try:
                        with open(main_go, "r") as f:
                            first_lines = f.read(500)
                            if "GOOS:" in first_lines:
                                # Extract supported OS
                                for line in first_lines.split("\n"):
                                    if "GOOS:" in line:
                                        supported = line.split(":")[-1].strip().lower()
                                        os_str = str(self.operating_system).lower()
                                        if (
                                            supported not in os_str
                                            and supported != "all"
                                        ):
                                            continue
                        available.append(entry)
                    except Exception as e:
                        logger.debug(f"Error checking module {entry}: {e}")
                        available.append(entry)  # Add anyway if we can't check

        return sorted(available)

    def is_module_available(self, module_name: str) -> bool:
        """
        Check if a specific module is available.

        Args:
            module_name: Name of the module to check

        Returns:
            bool: True if module is available, False otherwise
        """
        return module_name in self.get_available_modules()

    def load_module_beacon(self, userID: str) -> None:
        """
        Interactively load a module onto the beacon.

        Displays available modules and prompts user to select one,
        then queues it for loading on the beacon.

        Args:
            userID: Unique identifier for the beacon
        """
        available = self.get_available_modules()

        if not available:
            print("No modules available for this beacon's OS.")
            return

        print("\nAvailable modules:")
        for idx, mod in enumerate(available, 1):
            print(f"  {idx}. {mod}")

        # Set up tab completion for module names
        readline.set_completer(tab_completion(available))
        readline.parse_and_bind("tab: complete")

        try:
            choice = input("\nEnter module name or number (or 'cancel'): ").strip()

            if choice.lower() == "cancel":
                print("Cancelled.")
                return

            # Handle numeric choice
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available):
                    module_name = available[idx]
                else:
                    print(f"Invalid choice: {choice}")
                    return
            else:
                module_name = choice

            if module_name not in available:
                print(f"Module '{module_name}' not available.")
                return

            self.load_module_direct_beacon(userID, module_name)

        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
        finally:
            readline.set_completer(None)

    def load_module_direct_beacon(self, userID: str, module_name: str) -> None:
        """
        Load a specified module onto the beacon without user interaction.

        Reads the Go source code from the plugin's main.go file and queues it
        as a command for the beacon's interpreter to load.

        Args:
            userID: Unique identifier for the beacon
            module_name: Name of the module to load
        """

        # ----------------------------------------------------------------
        # Resolve Module Source Path
        # ----------------------------------------------------------------
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )
        plugin_dir = os.path.join(repo_plugins, module_name)

        if not os.path.isdir(plugin_dir):
            logger.error(
                f"Plugin directory for '{module_name}' not found at: {plugin_dir}"
            )
            print(f"Plugin directory for '{module_name}' not found.")
            return

        module_path = os.path.join(plugin_dir, "main.go")

        if not os.path.isfile(module_path):
            logger.error(
                f"Module source file for '{module_name}' not found at: {module_path}"
            )
            print(f"Module source file for '{module_name}' not found.")
            return

        # ----------------------------------------------------------------
        # Load and Queue Module
        # ----------------------------------------------------------------
        logger.debug(
            f"Loading interpreted module '{module_name}' for userID: {userID} "
            f"from path: {module_path}"
        )

        try:
            with open(module_path, "r", encoding="utf-8") as module_file:
                source_code = module_file.read()

            # Get obfuscated name if configured
            obf_name = module_name
            try:
                entry = obfuscation_map.get(module_name)
                if isinstance(entry, dict):
                    obf_name = entry.get("obfuscation_name") or module_name
            except Exception:
                obf_name = module_name

            # Queue module load command with Go source code
            add_beacon_command_list(
                userID,
                None,
                "module",
                self.database,
                {"name": obf_name, "data": source_code},
            )

            logger.debug(
                f"Interpreted module '{module_name}' queued for loading on userID: {userID}. "
                "Will be marked as loaded after beacon confirms."
            )
            print(f"Module '{module_name}' queued for loading.")
            # Note: Module is added to loaded_modules in response_handler.py
            # after the beacon confirms successful loading

        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading interpreted module '{module_name}': {e}")
            print(f"Error loading interpreted module '{module_name}': {e}")
            traceback.print_exc()
