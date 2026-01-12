
import re
from Modules.beacon.beacon_server.handlers import connection_handler, beacon_handler, response_handler


ROUTES = {
    'POST': [
        (re.compile(r"^/(?P<part1>[^/]+)/(?P<part2>[^/]+)/(?P<ad_param>.*ad.*)/api/v(?P<version>[1-9]|10)$"), connection_handler.handle_connection_request),  # noqa: E501
        (re.compile(r"^/(?P<part1>[^/]+)/(?P<ad_param>.*ad.*)/getLatest$"), connection_handler.handle_reconnect),
        (re.compile(r"^/updateReport/(?P<path1>[^/]+)/api/v(?P<version>[1-9]|10)$"), response_handler.handle_command_response),
    ],
    'GET': [
        (re.compile(r"^/checkUpdates/(?P<part1>[^/]+)/(?P<part2>[^/]+)$"), beacon_handler.handle_beacon_call_in),
    ]
}


def get_handler(method: str, path: str) -> tuple:
    """
    Retrieves the appropriate handler function for a given HTTP method and path.
    Args:
        method (str): The HTTP method (e.g., 'GET', 'POST')
        path (str): The request paths
    Returns:
        tuple: (handler function, match dict) or (None, None) if no match found
    """
    for pattern, handler in ROUTES.get(method, []):
        match = pattern.match(path)
        if match:
            return handler, match.groupdict()
    return None, None
