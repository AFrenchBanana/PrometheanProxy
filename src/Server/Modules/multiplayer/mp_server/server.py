"""
Multiplayer HTTP server main module.
Provides the MP_Socket class for managing the Flask-based multiplayer API.
"""

import os
import threading

from flask import Flask
from Modules.global_objects import logger

from .router import register_routes
from .utils import TokenManager, get_token_ttl_from_config


class MP_Socket:
    """
    HTTP (TLS) based multiplayer control server.

    Endpoints:
        POST /api/login {username, password} -> returns auth token
        GET  /api/status -> user + auth status
        GET  /api/connections -> active beacons/sessions
        GET  /api/connections/details?uuid=UUID -> detailed connection info
        GET  /api/commands?uuid=UUID -> available commands for implant/session
        POST /api/commands -> issue command to implant/session
        POST /api/logout -> invalidate current token

    Authentication:
        Provide token via Authorization: Bearer <token> header or ?token= query parameter.

    Token Model:
        One active token per user. Re-authentication rotates the token; any previous token
        for that user becomes invalid immediately.
    """

    def __init__(self, config):
        """
        Initialize the multiplayer HTTP server.

        Args:
            config: Configuration dictionary with server settings
        """
        self.config = config
        self.port = config["multiplayer"]["multiplayerPort"]

        if not (isinstance(self.port, int) and 1 <= self.port <= 65535):
            logger.error(
                f"Invalid port number: {self.port}. Must be between 1 and 65535."
            )
            raise ValueError("Invalid port number")

        self.address = (
            self.config["multiplayer"]["multiplayerListenAddress"],
            self.config["multiplayer"]["multiplayerPort"],
        )

        # Initialize Flask app
        self._app = Flask("PrometheanProxy-Multiplayer")

        # Initialize token manager
        token_ttl = get_token_ttl_from_config(config)
        self.token_manager = TokenManager(token_ttl_seconds=token_ttl)

        # Register routes
        register_routes(self._app, self)

        logger.info("Initialised HTTP multiplayer server (per-user token model)")

    def start(self):
        """Start the HTTPS Flask server in a background thread."""
        cert_dir = os.path.expanduser(self.config["server"]["TLSCertificateDir"])
        tls_key = os.path.join(cert_dir, self.config["server"]["TLSkey"])
        tls_cert = os.path.join(cert_dir, self.config["server"]["TLSCertificate"])

        if not (os.path.isfile(tls_key) and os.path.isfile(tls_cert)):
            logger.warning(
                "TLS key/cert not found; starting without TLS (development mode)"
            )
            ssl_context = None
        else:
            ssl_context = (tls_cert, tls_key)

        host, port = self.address

        def _run():
            logger.info(f"HTTP Multiplayer server listening on {host}:{port}")
            try:
                # threaded=True to allow multiple clients
                self._app.run(
                    host=host,
                    port=port,
                    ssl_context=ssl_context,
                    threaded=True,
                    use_reloader=False,
                )
            except Exception as e:
                logger.critical(f"Multiplayer HTTP server failed: {e}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def accept_connection(self):
        """
        Backwards compatibility method.

        Previous code expected accept_connection loop; this is a no-op now
        since Flask handles connections internally.
        """
        logger.debug("accept_connection called on HTTP implementation; no-op")
