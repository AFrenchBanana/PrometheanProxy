"""
Route registration for the multiplayer HTTP server.
Defines all API endpoints and maps them to their handlers.
"""

from .handlers import auth_handler, commands_handler, connections_handler


def register_routes(app, server):
    """
    Register all API routes for the multiplayer server.

    Args:
        app: The Flask application instance
        server: The MP_Socket server instance (passed to handlers for auth)
    """

    # --- Authentication Routes ---

    @app.post("/api/login")
    def login():
        """POST /api/login - Authenticate and receive token."""
        return auth_handler.handle_login(server)

    @app.post("/api/logout")
    def logout():
        """POST /api/logout - Invalidate current token."""
        return auth_handler.handle_logout(server)

    @app.get("/api/status")
    def status():
        """GET /api/status - Get current user and auth status."""
        return auth_handler.handle_status(server)

    # --- Connection Routes ---

    @app.get("/api/connections")
    def connections():
        """GET /api/connections - List active beacons/sessions."""
        return connections_handler.handle_connections(server)

    @app.get("/api/connections/details")
    def connection_details():
        """GET /api/connections/details - Get details for a specific connection."""
        return connections_handler.handle_connection_details(server)

    # --- Command Routes ---

    @app.get("/api/commands")
    def get_commands():
        """GET /api/commands - Get available commands for an implant/session."""
        return commands_handler.handle_get_commands(server)

    @app.post("/api/commands")
    def post_command():
        """POST /api/commands - Issue a command to an implant/session."""
        return commands_handler.handle_post_command(server)

    # --- Utility Routes ---

    @app.get("/ping")
    def ping():
        """GET /ping - Health check endpoint."""
        from flask import jsonify

        return jsonify({"pong": True})
