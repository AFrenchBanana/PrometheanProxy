import threading
from http.server import HTTPServer

from Modules.beacon.beacon_server.request_handler import BeaconRequestHandler
from Modules.beacon.beacon_server.websocket_server import start_websocket_server
from Modules.global_objects import get_database, logger


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


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

    # Initialize command database (creates tables on first use)
    try:
        get_database("command_database")
        logger.info("Command database initialized on server start")
    except Exception as e:
        logger.error(f"Failed to initialize command database: {e}")
        raise

    # --- REVERTED SSL LOGIC ---
    # The HTTPServer is now created directly without any SSL wrapping
    # to ensure it listens for plain HTTP, as required by the client.
    # Start WebSocket server (non-blocking) for live events/commands
    try:
        start_websocket_server(config)
        logger.info("Beacon WebSocket server started")
    except Exception as e:
        logger.warning(f"Failed to start Beacon WebSocket server: {e}")
    httpd = ReusableHTTPServer(server_address, BeaconRequestHandler)
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
