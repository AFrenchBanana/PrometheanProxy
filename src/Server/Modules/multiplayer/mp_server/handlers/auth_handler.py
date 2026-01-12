"""
Authentication handlers for the multiplayer HTTP server.
Provides login, logout, and status endpoints.
"""

from flask import jsonify, request
from Modules.global_objects import logger, multiplayer_connections
from Modules.utils.console import cprint

from ..utils import HTTPClientSession


def handle_login(server):
    """
    Handle user login request.

    POST /api/login {username, password} -> returns auth token

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with token or error
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    if server.authenticate_user(username, password):
        token_info = server.token_manager.issue_token(username)

        multiplayer_connections[username] = HTTPClientSession(
            username=username,
            token=token_info["token"],
            address=(request.remote_addr or "0.0.0.0", 0),
        )

        # Update user object if exists
        user_obj = (
            getattr(server, "users", {}).get(username)
            if hasattr(server, "users")
            else None
        )
        if user_obj:
            user_obj.auth_token = token_info["token"]
            user_obj.auth_token_expiry = token_info["expires"]

        cprint(
            f"User {username} authenticated via HTTP from {request.remote_addr}. "
            f"Token issued/rotated (expires {token_info['expires']}).",
            fg="green",
        )
        logger.info(f"HTTP multiplayer login success for {username}")

        return jsonify(
            {
                "token": token_info["token"],
                "expires": token_info["expires"],
                "user": username,
            }
        )
    else:
        logger.warning(f"Authentication failed for user {username}")
        return jsonify({"error": "Authentication failed"}), 401


def handle_logout(server):
    """
    Handle user logout request.

    POST /api/logout -> invalidate current token

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with status or error
    """
    token = _get_token_from_request()
    if not token:
        return jsonify({"error": "Invalid token"}), 401

    username = server.token_manager.invalidate_token(token)
    if not username:
        return jsonify({"error": "Invalid token"}), 401

    multiplayer_connections.pop(username, None)

    # Clear token on user object if exists
    user_obj = (
        getattr(server, "users", {}).get(username) if hasattr(server, "users") else None
    )
    if user_obj:
        user_obj.auth_token = None
        user_obj.auth_token_expiry = None

    return jsonify({"status": "ok"})


def handle_status(server):
    """
    Handle status request.

    GET /api/status -> user + auth status

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with user status or error
    """
    username = require_auth(server)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    token_info = server.token_manager.get_token_info(username)
    expires_iso = token_info.get("expires") if token_info else None
    remaining = token_info.get("expires_in") if token_info else None

    return jsonify(
        {
            "user": username,
            "authenticated": True,
            "expires": expires_iso,
            "expires_in": remaining,
        }
    )


def _get_token_from_request():
    """
    Extract token from request headers, query params, or cookies.

    Returns:
        The token string or None
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(None, 1)[1].strip()
    return request.args.get("token") or request.cookies.get("pp_token")


def require_auth(server):
    """
    Validate authentication for the current request.

    Args:
        server: The MP_Socket server instance

    Returns:
        The username if authenticated, None otherwise
    """
    token = _get_token_from_request()
    return server.token_manager.validate_token(token)
