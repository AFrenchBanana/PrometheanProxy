
import os
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import command_list, logger
from Modules.beacon_server.socket_manager import socketio
from Modules.beacon_server.utils import process_request_data


def handle_command_response(handler: BaseHTTPRequestHandler, match: dict):
    """Receives the output from an executed command."""
    logger.info(f"Response received from {handler.path}")

    content_len = int(handler.headers.get('Content-Length', 0))
    raw_data = handler.rfile.read(content_len)

    data, error = process_request_data(raw_data)
    if error:
        handler.send_response(400)
        handler.end_headers()
        return

    reports = data.get('reports', [])
    if not reports or 'command_uuid' not in reports[0]:
        logger.error("Invalid report format received.")
        handler.send_response(400)
        handler.end_headers()
        return

    cid = reports[0]['command_uuid']
    output = reports[0]['output']
    command = command_list.get(cid)

    if not command:
        logger.error(f"Command with UUID {cid} not found in command list.")
        handler.send_response(500)
        handler.end_headers()
        return

    command.command_output = output
    socketio_event = 'command_response'

    if command.command == "directory_traversal":
        socketio_event = "directory_traversal"
        dir_path = os.path.expanduser(f"~/.PrometheanProxy/{command.beacon_uuid}")
        os.makedirs(dir_path, exist_ok=True)
        with open(os.path.join(dir_path, "directory_traversal.json"), "w") as f:
            f.write(output)
        logger.info(f"Directory Traversal response for {command.beacon_uuid} saved.")

    socketio.emit(socketio_event, {
        'uuid': command.beacon_uuid, 'command_id': command.command_uuid,
        'command': command.command, 'response': output
    })
    logger.info(f"Emitted '{socketio_event}' event for command {cid}.")

    handler.send_response(200)
    handler.end_headers()
