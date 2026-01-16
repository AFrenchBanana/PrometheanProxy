"""
Connection handlers for the multiplayer HTTP server.
Provides endpoints for listing and querying active connections.
"""

from flask import jsonify, request
from Modules.beacon.beacon import command_list
from Modules.global_objects import beacon_list, logger, sessions_list

from .auth_handler import require_auth


def handle_connections(server):
    """
    Handle connections listing request.

    GET /api/connections -> active beacons/sessions
    Query params:
        - filter: "beacons" or "sessions" to filter results

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with connections list or error
    """
    username = require_auth(server)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    connections_filter = request.args.get("filter")
    if connections_filter and connections_filter not in ["beacons", "sessions"]:
        return jsonify({"error": "Invalid filter"}), 400

    return jsonify(_get_active_connections(connections_filter))


def handle_connection_details(server):
    """
    Handle connection details request.

    GET /api/connections/details?uuid=UUID -> detailed info for a specific connection
    Query params:
        - uuid: Required, the connection UUID
        - commands: Optional, if present includes command history

    Args:
        server: The MP_Socket server instance

    Returns:
        Flask response with connection details or error
    """
    username = require_auth(server)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    uuid = request.args.get("uuid")
    if not uuid:
        return jsonify({"error": "Missing uuid"}), 400

    data = {}

    # Get connection info
    connection_info = _get_connection_by_uuid(uuid)
    if connection_info:
        data["connection"] = connection_info

    # Include commands if requested
    if request.args.get("commands") is not None:
        commands = []
        for command in command_list.values():
            if getattr(command, "beacon_uuid", None) == uuid:
                commands.append(
                    {
                        "command_uuid": getattr(command, "command_uuid", None),
                        "command": getattr(command, "command", None),
                        "data": getattr(command, "command_data", None),
                        "executed": getattr(command, "executed", False),
                        "output": getattr(command, "command_output", None),
                    }
                )
        data["commands"] = commands

    return jsonify(data)


def _get_active_connections(filter_type):
    """
    Get active connections (beacons and/or sessions).

    Args:
        filter_type: "beacons", "sessions", or None for both

    Returns:
        dict with beacons and/or sessions lists
    """
    logger.debug(f"Fetching active connections with filter: {filter_type}")

    result = {}

    if filter_type == "beacons" or filter_type is None:
        beacons = []
        for userID, beacon in beacon_list.items():
            beacons.append(
                {
                    "userID": userID,
                    "uuid": getattr(beacon, "uuid", None),
                    "address": getattr(beacon, "address", None),
                    "hostname": getattr(beacon, "hostname", None),
                    "operating_system": getattr(beacon, "operating_system", None),
                    "last_beacon": getattr(beacon, "last_beacon", None),
                    "next_beacon": getattr(beacon, "next_beacon", None),
                    "timer": getattr(beacon, "timer", None),
                    "jitter": getattr(beacon, "jitter", None),
                    "loaded_modules": getattr(beacon, "loaded_modules", []),
                }
            )
        result["beacons"] = beacons

    if filter_type == "sessions" or filter_type is None:
        sessions = []
        for userID, session in sessions_list.items():
            sessions.append(
                {
                    "userID": userID,
                    "address": getattr(session, "address", None),
                    "hostname": getattr(session, "hostname", None),
                    "operating_system": getattr(session, "operating_system", None),
                    "mode": getattr(session, "mode", None),
                    "load_modules": getattr(session, "load_modules", None),
                }
            )
        result["sessions"] = sessions

    return result


def _get_connection_by_uuid(uuid):
    """
    Get connection info by UUID.

    Args:
        uuid: The connection UUID to look up

    Returns:
        dict with connection info or None if not found
    """
    # Check beacons
    for userID, beacon in beacon_list.items():
        beacon_uuid = getattr(beacon, "uuid", None) or userID
        if beacon_uuid == uuid:
            return {
                "type": "beacon",
                "userID": userID,
                "uuid": beacon_uuid,
                "address": getattr(beacon, "address", None),
                "hostname": getattr(beacon, "hostname", None),
                "operating_system": getattr(beacon, "operating_system", None),
                "last_beacon": getattr(beacon, "last_beacon", None),
                "next_beacon": getattr(beacon, "next_beacon", None),
                "timer": getattr(beacon, "timer", None),
                "jitter": getattr(beacon, "jitter", None),
                "loaded_modules": getattr(beacon, "loaded_modules", []),
            }

    # Check sessions
    for userID, session in sessions_list.items():
        session_uuid = getattr(session, "uuid", None) or userID
        if session_uuid == uuid:
            return {
                "type": "session",
                "userID": userID,
                "uuid": session_uuid,
                "address": getattr(session, "address", None),
                "hostname": getattr(session, "hostname", None),
                "operating_system": getattr(session, "operating_system", None),
                "mode": getattr(session, "mode", None),
                "load_modules": getattr(session, "load_modules", None),
            }

    return None
