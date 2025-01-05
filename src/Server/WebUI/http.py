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
    add_beacon_command_list)
import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
log = logging.getLogger('werkzeug')
app.logger.setLevel(logging.ERROR)
log.setLevel(logging.ERROR)


@socketio.on('join')
def handle_join(data):
    uuid = data
    join_room(uuid)
    app.logger.info(f"Client joined room: {uuid}")


@app.route('/api/v1/beacons', methods=['GET', 'POST'])  # Added 'POST' method
def api_beacons():
    # Log incoming request method and IP
    app.logger.info(f"Received {request.method} request from {request.remote_addr}") # noqa
    if request.remote_addr != '127.0.0.1':
        app.logger.warning("Access denied from non-local address.")
        return jsonify({"error": "Access denied"}), 403

    if request.method == 'POST' and request.args.get('command'):
        app.logger.info("Command API called via POST")
        uuid = request.args.get('command')
        try:
            request_data = request.get_json()
            beacon_uuid = request_data.get('command_id')
            app.logger.debug(f"Command UUID: {uuid}, Data: {request_data}")
            if request_data and "task" in request_data:
                add_beacon_command_list(uuid,
                                        beacon_uuid, request_data["task"],
                                        request_data["data"])
                app.logger.info(f"Command added for UUID: {uuid}")
                socketio.emit('command_response', {
                    'uuid': uuid,
                    'command_id': request_data["command_id"],
                    'command': request_data["task"],
                    'response': request_data["data"]
                }, room=uuid)
                return jsonify({"status": "Command added"})
            else:
                app.logger.error("No data provided in POST request.")
                return jsonify({"error": "No data provided"}), 400
        except KeyError as e:
            return jsonify({"error": f"Missing key: {str(e)}"}), 400

    elif request.method == 'GET':
        if request.args.get('history'):
            uuid = request.args.get('history')
            # Removed redundant userID assignment
            history_data = []
            for command in command_list.values():
                if command.beacon_uuid == uuid:
                    history_data.append({
                        "command_id": command.command_uuid,
                        "command": command.command,
                        "response": command.command_output,
                    })
            return jsonify({"history": history_data})
        else:
            # Handle GET requests without 'history' parameter
            beacons_grouped = {}
            # Loop through the beacons and group them by UUID
            for beaconID, beacon in beacon_list.items():
                beacons_grouped[beaconID] = {
                    "address": beacon.address,
                    "hostname": beacon.hostname,
                    "operating_system": beacon.operating_system,
                    "last_beacon": beacon.last_beacon,
                    "next_beacon": beacon.next_beacon,
                    "timer": beacon.timer,
                    "jitter": beacon.jitter
                }
            app.logger.info("Beacons data retrieved via GET")
            return jsonify({"beacons": beacons_grouped})

    else:
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
        return jsonify({"beacon": beacon_data})
    else:
        return jsonify({"error": "Beacon not found"}), 404


@app.route('/beacons')
def beacon():
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
                break
        if beacon_data:
            return render_template('beacon.html', beacon=beacon_data,
                                   uuid=uuid)
        else:
            return redirect('/')
    else:
        return redirect('/')


@app.route('/')
def index():
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
