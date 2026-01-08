from http.server import BaseHTTPRequestHandler
from Modules.global_objects import logger
from urllib.parse import urlparse
from .router import get_handler


class BeaconRequestHandler(BaseHTTPRequestHandler):
    """
    Custom HTTP request handler for beacon server.
    Routes requests to appropriate handlers based on method and path.
    Args:
        BaseHTTPRequestHandler: Inherited HTTP request handler class
    Returns:
        None
    """
    def _route_request(self, method: str):
        parsed_url = urlparse(self.path)
        path_only = parsed_url.path

        # Use the path_only for routing, ignoring the query string
        handler, match = get_handler(method, path_only)
        if handler:
            # The handler function is called successfully
            handler(self, match)
        else:
            # This will now only trigger for genuinely unmatched beacon URLs
            self.send_response(404)
            self.end_headers()
            logger.warning(f"404 - No handler found for {method} {path_only}")

    def do_GET(self):
        self._route_request('GET')

    def do_POST(self):
        self._route_request('POST')

    def log_message(self, format, *args):
        # Suppress the default http.server logging to keep the output clean
        return
