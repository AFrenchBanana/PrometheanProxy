"""
Command handlers for the multiplayer HTTP server.
Provides endpoints for querying and issuing commands to implants/sessions.
"""

from flask import jsonify, request
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import beacon_list, logger, sessions_list

from .auth_handler import require_auth


def handle_get_commands(server):
    """
    Handle available commands request.

    GET /api/commands?uuid=UUID -> available commands for implant/session

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with available commands or error
    """
    username = require_auth(server)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    uuid = request.args.get("uuid")
    if not uuid:
        return jsonify({"error": "Missing uuid"}), 400

    return jsonify({"response": _get_available_commands(uuid)})


def handle_post_command(server):
    """
    Handle command issuance request.

    POST /api/commands {uuid, command, data} -> issue command to implant/session

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with status or error
    """
    username = require_auth(server)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        request_data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    uuid = request_data.get("uuid")
    data = request_data.get("data")
    command = request_data.get("command")

    if not uuid or not command:
        return jsonify({"error": "Missing uuid or command"}), 400

    available_commands = _get_available_commands(uuid)
    if isinstance(available_commands, dict) and "error" in available_commands:
        return jsonify(available_commands), 400

    if command not in available_commands:
        return jsonify({"error": "Invalid command for given UUID"}), 400

    try:
        # Get the beacon object to access its database
        beacon_obj = beacon_list.get(uuid)
        if not beacon_obj:
            return jsonify({"error": "Beacon not found"}), 404

        add_beacon_command_list(uuid, None, command, beacon_obj.database, data)
        logger.info(f"Command '{command}' issued to {uuid} by {username}")
    except Exception as e:
        logger.error(f"Failed to add command to beacon/session {uuid}: {e}")
        return jsonify({"error": "Failed to add command"}), 500

    return jsonify({"status": "command issued", "uuid": uuid, "command": command})


def _get_available_commands(implant_uuid):
    """
    Get available commands for a specific implant/session.

    Args:
        implant_uuid: The UUID of the implant or session

    Returns:
        list of available commands or dict with error
    """
    available_commands = {"beacon": ["test"], "session": ["test2"]}

    # Check beacons
    for userID, beacon in beacon_list.items():
        beacon_uuid = getattr(beacon, "uuid", None) or userID
        if beacon_uuid == implant_uuid:
            mode = getattr(beacon, "mode", "beacon")
            return available_commands.get(mode, available_commands.get("beacon"))

    # Check sessions
    for userID, session in sessions_list.items():
        session_uuid = getattr(session, "uuid", None) or userID
        if session_uuid == implant_uuid:
            mode = getattr(session, "mode", "session")
            return available_commands.get(mode, available_commands.get("session"))

    return {"error": "Invalid UUID"}
