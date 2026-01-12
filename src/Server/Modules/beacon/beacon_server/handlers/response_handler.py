import os
import colorama
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import command_list, logger, obfuscation_map, command_database
from Modules.beacon.beacon_server.utils import process_request_data
from Modules.utils.ui_manager import log_connection_event, RichPrint


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

        if command_database is not None:
            command_database.update_entry(
                "beacon_commands",
                "executed=?, command_output=?",
                (True, output),
                "command_uuid=?",
                (cid,)
            )
            logger.debug(f"Updated command {cid} status to 'Completed' with output")
        else:
            logger.warning(f"Command database not initialized yet, skipping database update for command {cid}")


        command.command_output = output

        # Log to live events panel and terminal
        truncated_output = output[:50] + "..." if len(output) > 50 else output
        log_connection_event(
            "command_output",
            f"{command.command}: {truncated_output}",
            {"command_uuid": cid, "command": command.command, "output": output}
        )
        RichPrint.r_print(f"[bright_green]✓[/] Command [bright_cyan]{command.command}[/] completed")

        if command.command == "module":
            command.data = ""

    handler.send_response(200)
    handler.end_headers()
