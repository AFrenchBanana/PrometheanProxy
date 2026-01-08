import threading
from http.server import HTTPServer

from Modules.beacon.beacon_server.request_handler import BeaconRequestHandler
from Modules.global_objects import logger


def run_http_server(config):
    """
    Starts the HTTP server for handling beacon requests.
    Args:
        config (dict): Configuration dictionary
    Returns:
        None
    """
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
    Starts the beacon HTTP server in a separate thread.
    Args:
        config (dict): Configuration dictionary
    Returns:
        None
    """
    run_http_server(config)
