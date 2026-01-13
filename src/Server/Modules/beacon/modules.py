# ============================================================================
# Beacon Modules Module
# ============================================================================
# This module provides functionality for loading and managing modules on beacons,
# including interactive module selection and direct module loading.
# ============================================================================

# Standard Library Imports
import base64
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
    commands for beacons to execute.
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

        Searches for modules in the configured module location and repo plugins
        directory, supporting both legacy and unified directory structures.

        Returns:
            List of available module names
        """
        command_location = self._resolve_module_base()
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )

        module_names: list[str] = []

        try:
            # ----------------------------------------------------------------
            # Determine Platform-Specific Settings
            # ----------------------------------------------------------------
            os_str = str(self.operating_system).lower()
            platform_folder = "windows" if "windows" in os_str else "linux"
            ext = ".dll" if platform_folder == "windows" else ".so"
            channel = "debug" if "debug" in os_str else "release"

            # ----------------------------------------------------------------
            # Discover Available Modules
            # ----------------------------------------------------------------
            # Legacy structure has OS folders at root (linux/windows/<channel>/*.ext)
            legacy_linux = os.path.join(command_location, "linux")
            legacy_windows = os.path.join(command_location, "windows")

            if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                # Legacy structure
                files: list[str] = []
                for ch in ("release", "debug"):
                    d = os.path.join(command_location, platform_folder, ch)
                    if os.path.isdir(d):
                        files.extend([f for f in os.listdir(d) if f.endswith(ext)])
                module_names = [
                    os.path.splitext(f)[0].removesuffix("-debug") for f in files
                ]
            else:
                # Unified structure: <name>/{release,debug}/{name}[-debug].ext
                if os.path.isdir(command_location):
                    for name in os.listdir(command_location):
                        full = os.path.join(command_location, name)
                        if not os.path.isdir(full):
                            continue
                        fname = f"{name}{'-debug' if channel == 'debug' else ''}{ext}"
                        cand = os.path.join(full, channel, fname)
                        if os.path.isfile(cand):
                            module_names.append(name)

                # Fallback to repo tree if none found in user directory
                if not module_names and os.path.isdir(repo_plugins):
                    for name in os.listdir(repo_plugins):
                        full = os.path.join(repo_plugins, name)
                        if not os.path.isdir(full):
                            continue
                        fname = f"{name}{'-debug' if channel == 'debug' else ''}{ext}"
                        cand = os.path.join(full, channel, fname)
                        if os.path.isfile(cand):
                            module_names.append(name)

        except Exception as e:
            logger.error(f"Error discovering modules: {e}")

        return sorted(set(module_names))

    def is_module_available(self, module_name: str) -> bool:
        """
        Check if a module is available for loading.

        Args:
            module_name: Name of the module to check

        Returns:
            True if the module is available, False otherwise
        """
        return module_name in self.get_available_modules()

    def load_module_beacon(self, userID: str) -> None:
        """
        Interactively load a module onto the beacon.

        Presents the user with a list of available modules for the beacon's
        operating system and loads the selected module.

        Args:
            userID: Unique identifier for the beacon
        """
        command_location = self._resolve_module_base()

        try:
            module_names = self.get_available_modules()

            # Display available modules
            print("Available modules:")
            for name in module_names:
                print(f" - {name}")

        except Exception as e:
            logger.error(f"Error listing modules in {command_location}: {e}")
            print(f"Error listing modules in {command_location}: {e}")
            return

        # ----------------------------------------------------------------
        # Get User Selection
        # ----------------------------------------------------------------
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, list(module_names) + ["exit"]
            )
        )
        module_name = input("Enter the module name to load: ")
        if not module_name:
            print("No module name provided.")
            return
        if module_name in self.loaded_modules:
            print(f"Module '{module_name}' is already loaded.")
            return

        logger.debug(f"Loading module '{module_name}' for userID: {userID}")
        self.load_module_direct_beacon(userID, module_name)

    def load_module_direct_beacon(self, userID: str, module_name: str) -> None:
        """
        Load a specified module onto the beacon without user interaction.

        Resolves the module file path, reads the module binary, encodes it,
        and queues it as a command for the beacon to load.

        Args:
            userID: Unique identifier for the beacon
            module_name: Name of the module to load
        """

        # ----------------------------------------------------------------
        # Resolve Module Path
        # ----------------------------------------------------------------
        command_location = os.path.abspath(self._resolve_module_base())
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )
        os_str = str(self.operating_system).lower()
        platform_folder = "windows" if "windows" in os_str else "linux"
        ext = ".dll" if platform_folder == "windows" else ".so"
        channel = "debug" if "debug" in os_str else "release"

        # Unified layout: <name>/{release,debug}/{name}[-debug].ext
        filename = f"{module_name}{'-debug' if channel == 'debug' else ''}{ext}"
        module_path = os.path.join(command_location, module_name, channel, filename)

        # ----------------------------------------------------------------
        # Fallback to Legacy Structure if Needed
        # ----------------------------------------------------------------
        if not os.path.isfile(module_path):
            legacy_base = os.path.expanduser(
                self.config["server"].get("module_location", "")
            )
            legacy_try = os.path.join(
                legacy_base,
                "windows" if platform_folder == "windows" else "linux",
                channel,
                f"{module_name}{'-debug' if channel == 'debug' else ''}{ext}",
            )
            if os.path.isfile(legacy_try):
                module_path = legacy_try

        # Fallback to repo tree if still missing
        if not os.path.isfile(module_path) and os.path.isdir(repo_plugins):
            repo_try = os.path.join(repo_plugins, module_name, channel, filename)
            if os.path.isfile(repo_try):
                module_path = repo_try

        if not os.path.isfile(module_path):
            logger.error(
                f"Module file for '{module_name}' not found in expected locations."
            )
            print(f"Module file for '{module_name}' not found.")
            return

        # ----------------------------------------------------------------
        # Load and Queue Module
        # ----------------------------------------------------------------
        module_path = os.path.abspath(os.path.expanduser(module_path))
        logger.debug(
            f"Loading module '{module_name}' for userID: {userID} "
            f"from path: {module_path}"
        )
        try:
            with open(module_path, "rb") as module_file:
                file_data = module_file.read()
                file_data = base64.b64encode(file_data).decode("utf-8")

                # Get obfuscated name if configured
                obf_name = module_name
                try:
                    entry = obfuscation_map.get(module_name)
                    if isinstance(entry, dict):
                        obf_name = entry.get("obfuscation_name") or module_name
                except Exception:
                    obf_name = module_name

                # Queue module load command
                add_beacon_command_list(
                    userID,
                    None,
                    "module",
                    self.database,
                    {"name": obf_name, "data": file_data},
                )

            logger.debug(
                f"Module '{module_name}' queued for loading on userID: {userID}. "
                "Will be marked as loaded after beacon confirms."
            )
            # Note: Module is added to loaded_modules in response_handler.py
            # after the beacon confirms successful loading

        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")
            traceback.print_exc()
