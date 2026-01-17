# ============================================================================
# Beacon History Module
# ============================================================================
# This module provides command history viewing and beacon configuration
# functionality for beacons.
# ============================================================================

# Standard Library Imports
import ast

# Third-Party Imports
import colorama

# Local Module Imports
from ..global_objects import command_list, logger, obfuscation_map
from .registry import add_beacon_command_list


class HistoryMixin:
    """
    Mixin class providing command history and configuration functionality.

    This mixin provides methods for viewing command history from the database
    and configuring beacon parameters like timer and jitter.
    """

    def list_db_commands(self, userID: str) -> None:
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
                output = (
                    beacon_commands.command_output
                    if beacon_commands.command_output
                    else "Awaiting Response"
                )
                if output == "Received":
                    status_display = (
                        colorama.Fore.CYAN + "Status: Received (waiting for output)"
                    )
                elif output == "Awaiting Response":
                    status_display = colorama.Fore.YELLOW + "Status: Awaiting Response"
                else:
                    # Truncate long output
                    max_len = 100
                    display_output = (
                        output if len(output) <= max_len else output[:max_len] + "..."
                    )
                    status_display = (
                        colorama.Fore.GREEN
                        + f"Status: Completed\n                    Output: "
                        f"{colorama.Fore.WHITE}{display_output}"
                    )

                print(
                    f"""{colorama.Fore.WHITE}Command ID: {colorama.Fore.BLUE}{beacon_commands.command_uuid}
                    Command: {colorama.Fore.MAGENTA}{beacon_commands.command}
                    {status_display}"""
                )
        return

    def history(self, userID: str) -> None:
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
            try:
                self.database.dbconnection.commit()
            except Exception as e:
                logger.debug(
                    f"Commit before query (expected if no pending transactions): {e}"
                )

            # Create a fresh cursor to ensure we get the latest data
            fresh_cursor = self.database.dbconnection.cursor()

            # Query database for all commands for this beacon
            placeholder = "%s" if self.database.db_type == "postgresql" else "?"
            query = (
                "SELECT command, command_uuid, executed, command_output, command_data "
                f"FROM beacon_commands WHERE beacon_uuid = {placeholder}"
            )
            fresh_cursor.execute(query, (userID,))
            commands = fresh_cursor.fetchall()
            fresh_cursor.close()

            if not commands:
                print(
                    colorama.Fore.YELLOW
                    + f"No command history found for beacon {userID}"
                )
                logger.info(f"No command history found for beacon {userID}")
                return

            # Display header
            print(colorama.Fore.CYAN + "\n" + "=" * 80)
            print(colorama.Fore.CYAN + f"Command History for Beacon: {userID}")
            print(colorama.Fore.CYAN + "=" * 80)

            # Display each command
            for idx, (command, cmd_uuid, executed, output, command_data) in enumerate(
                commands, 1
            ):
                # Check in-memory command_list first for most up-to-date status
                in_memory_cmd = command_list.get(cmd_uuid)
                if in_memory_cmd and in_memory_cmd.command_output:
                    # Use in-memory output if available (more current than DB)
                    output = in_memory_cmd.command_output
                    executed = in_memory_cmd.executed

                # Debug logging to see actual database values
                logger.debug(
                    f"Command {idx}: executed={executed} (type={type(executed)}), "
                    f"output={output[:50] if output else 'None'}..."
                )

                # Determine status based on executed flag and output content
                has_real_output = output and output not in [
                    "Received",
                    "Awaiting Response",
                    "Command received by beacon",
                    "",
                ]

                if executed is True or executed == 1 or has_real_output:
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
                        data = (
                            ast.literal_eval(command_data)
                            if isinstance(command_data, str)
                            else command_data
                        )
                        if isinstance(data, dict) and "name" in data:
                            obf_module_name = data["name"]
                            # Deobfuscate the module name
                            real_module_name = deobfuscate_module_name(obf_module_name)
                            display_command = f"Load Module: {real_module_name}"
                    except Exception as e:
                        logger.debug(f"Failed to parse module command data: {e}")
                        display_command = command

                print(
                    f"\n{colorama.Fore.WHITE}[{idx}] Command: "
                    f"{colorama.Fore.MAGENTA}{display_command}"
                )
                print(f"    UUID: {colorama.Fore.BLUE}{cmd_uuid}")
                print(f"    Status: {status}")

                # Show actual output based on status
                if executed is True or executed == 1 or has_real_output:
                    # Command has been executed - show actual output
                    max_output_len = 500
                    display_output = (
                        output
                        if len(output) <= max_output_len
                        else output[:max_output_len] + "..."
                    )
                    print(f"    Output: {colorama.Fore.WHITE}{display_output}")
                elif output == "Received":
                    print(f"    Output: {colorama.Fore.CYAN}{output}")
                elif output == "Awaiting Response":
                    print(f"    Output: {colorama.Fore.YELLOW}{output}")
                else:
                    print(
                        f"    Output: {colorama.Fore.YELLOW}"
                        f"{output if output else 'Pending'}"
                    )

            print(colorama.Fore.CYAN + "\n" + "=" * 80 + "\n")
            logger.info(
                f"Displayed {len(commands)} commands from history for beacon {userID}"
            )

        except Exception as e:
            logger.error(f"Error retrieving command history for beacon {userID}: {e}")
            print(colorama.Fore.RED + f"Error retrieving command history: {e}")

        return

    def beacon_configuration(self, userID: str) -> None:
        """
        Configure beacon parameters interactively.

        Prompts the user to enter configuration commands and values (e.g.,
        timer, jitter) and queues them as a configuration command for the beacon.

        Args:
            userID: Unique identifier for the beacon
        """
        logger.debug(f"Configuring beacon for userID: {userID}")
        data = {}

        while True:
            command = input("Enter Configuration command: ")
            value = input("Enter configuration value: ")
            logger.debug(f"Adding configuration command: {command} with value: {value}")

            if value.isdigit():
                value = int(value)
                data[command] = value
            else:
                print("Value must be an integer")

            if input("Add another configuration option? (y/N)").lower() == "y":
                continue
            else:
                break

        logger.debug(f"Final configuration data: {data}")
        add_beacon_command_list(
            userID, None, "beacon_configuration", self.database, data
        )
        return
