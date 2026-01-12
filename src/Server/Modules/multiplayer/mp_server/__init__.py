"""
Multiplayer HTTP server module.

This module provides a Flask-based HTTP(S) API server for multiplayer
functionality, allowing remote clients to authenticate and interact
with the PrometheanProxy server.

Module Structure:
    - server.py: Main MP_Socket class and server startup logic
    - router.py: Route registration for all API endpoints
    - utils.py: Token management and utility functions
    - handlers/: Request handlers for API endpoints
        - auth_handler.py: Authentication (login, logout, status)
        - connections_handler.py: Connection management (list, details)
        - commands_handler.py: Command management (list, issue)

Usage:
    from Modules.multiplayer.mp_server import MP_Socket

    server = MP_Socket(config)
    server.start()
"""

from .server import MP_Socket
from .utils import HTTPClientSession, TokenManager

__all__ = ["MP_Socket", "HTTPClientSession", "TokenManager"]
