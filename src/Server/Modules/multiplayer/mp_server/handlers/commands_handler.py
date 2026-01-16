"""
Command handlers for the multiplayer HTTP server.
Provides endpoints for querying and issuing commands to implants/sessions.
"""

from flask import jsonify, request
from Modules.beacon.beacon import add_beacon_command_list
from Modules.global_objects import beacon_list, logger, sessions_list

from .auth_handler import require_auth


def _get_multihandler_commands():
    """
    Get the MultiHandlerCommands instance to access loaded plugins.

    Returns:
        MultiHandlerCommands instance or None if not available
    """
    try:
        from Modules.global_objects import config
        from Modules.multi_handler.multi_handler_commands import MultiHandlerCommands

        # Create a temporary instance just to get commands
        # In a real implementation, this should be cached/singleton
        temp_handler = MultiHandlerCommands(config, None)
        return temp_handler
    except Exception as e:
        logger.error(f"Failed to get multihandler commands: {e}")
        return None


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

    logger.debug(f"Command request - UUID: {uuid}, Command: {command}, Data: {data}")

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

        # Handle special case for load_module command
        if command == "load_module":
            # For load_module, data should contain the module name
            if not data:
                return jsonify({"error": "Module name required for load_module"}), 400

            # Extract module name from data
            if isinstance(data, dict):
                module_name = data.get("name") or data.get("module")
            else:
                module_name = str(data)

            if not module_name:
                return jsonify({"error": "Module name not provided"}), 400

            # Queue the load_module command with proper format
            command_data = {"name": module_name}
            add_beacon_command_list(
                uuid, None, "load_module", beacon_obj.database, command_data
            )
            logger.info(
                f"Module load command issued to {uuid} by {username}: {module_name}"
            )
            return jsonify(
                {"status": "module load queued", "uuid": uuid, "module": module_name}
            )

        # Ensure data is properly formatted for other commands
        # If data is None, pass None (will be converted to {} in add_beacon_command_list)
        # If data is a string, wrap it in a dict
        # If data is already a dict, use as-is
        command_data = None
        if data is not None:
            if isinstance(data, str):
                command_data = {"args": data} if data else None
            elif isinstance(data, dict):
                command_data = data
            else:
                # For other types, convert to string and wrap
                command_data = {"data": str(data)}

        add_beacon_command_list(uuid, None, command, beacon_obj.database, command_data)
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
    # Get commands from multihandler plugins
    handler = _get_multihandler_commands()

    if handler:
        beacon_commands = handler.list_loaded_beacon_commands()
        session_commands = handler.list_loaded_session_commands()
    else:
        # Fallback to basic commands if multihandler not available
        beacon_commands = ["shell", "close", "session", "sysinfo"]
        session_commands = ["shell", "close", "beacon", "sysinfo"]

    # Add built-in commands that are always available
    beacon_commands_full = list(
        set(
            beacon_commands
            + ["shell", "close", "session", "shutdown", "sysinfo", "load_module"]
        )
    )
    session_commands_full = list(
        set(
            session_commands
            + ["shell", "close", "beacon", "shutdown", "sysinfo", "load_module"]
        )
    )

    available_commands = {
        "beacon": sorted(beacon_commands_full),
        "session": sorted(session_commands_full),
    }

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
