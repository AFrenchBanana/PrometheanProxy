import threading
from http.server import HTTPServer

from Modules.beacon.beacon_server.request_handler import BeaconRequestHandler
from Modules.beacon.beacon_server.socket_manager import socketio, socket_flask_app
from Modules.global_objects import logger


def run_http_server(config):
    """Starts the main HTTP server."""
    host = '0.0.0.0'
    port = config["server"]["webPort"]
    server_address = (host, port)

    # --- REVERTED SSL LOGIC ---
    # The HTTPServer is now created directly without any SSL wrapping
    # to ensure it listens for plain HTTP, as required by the client.
    httpd = HTTPServer(server_address, BeaconRequestHandler)
    logger.info(f"Starting HTTP beacon server on http://{host}:{port}")
    # --- END REVERSION ---

    httpd.serve_forever()


def run_socketio_server(config):
    """Starts the Socket.IO server in the background."""
    host = '0.0.0.0'
    # Use a different port for the WebSocket server
    socket_port = config['server'].get('socket_port', 9001)

    logger.info(f"Starting WebSocket (Socket.IO) server on port {socket_port}")
    socketio.run(socket_flask_app, host=host, port=socket_port, allow_unsafe_werkzeug=True)


def start_beacon_server(config):
    """
    Main entry point to start both the beacon HTTP and Socket.IO servers.
    """
    socket_thread = threading.Thread(
        target=run_socketio_server,
        args=(config,),
        daemon=True
    )
    socket_thread.start()

    run_http_server(config)
