import threading
from http.server import HTTPServer

from Modules.beacon.beacon_server.request_handler import BeaconRequestHandler
from Modules.beacon.beacon_server.socket_manager import socketio, socket_flask_app
from Modules.global_objects import logger


def run_http_server(config):
    """Starts the main HTTP server."""
    host = config["server"]["listenaddress"]
    port = config["server"]["webPort"]
    server_address = (host, port)

    # --- REVERTED SSL LOGIC ---
    # The HTTPServer is now created directly without any SSL wrapping
    # to ensure it listens for plain HTTP, as required by the client.
    httpd = HTTPServer(server_address, BeaconRequestHandler)
    logger.info(f"Starting HTTP beacon server on http://{host}:{port}")
    # --- END REVERSION ---

    httpd.serve_forever()


def start_beacon_server(config):
    """
    Main entry point to start both the beacon HTTP and Socket.IO servers.
    """
    run_http_server(config)
