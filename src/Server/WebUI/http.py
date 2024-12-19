from flask import Flask, render_template, jsonify, request, redirect, make_response
from flask_socketio import SocketIO
from Modules.global_objects import beacons, beacon_commands, add_beacon_command_list
import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
log = logging.getLogger('werkzeug')
app.logger.setLevel(logging.ERROR)
log.setLevel(logging.ERROR)


@app.route('/api/v1/beacons', methods=['GET', 'POST'])  # Added 'POST' method
def api_beacons():
    # Log incoming request method and IP
    app.logger.info(f"Received {request.method} request from {request.remote_addr}")
    
    if request.remote_addr != '127.0.0.1':
        app.logger.warning("Access denied from non-local address.")
        return jsonify({"error": "Access denied"}), 403

    if request.method == 'POST' and request.args.get('command'):
        app.logger.info("Command API called via POST")
        uuid = request.args.get('command')
        request_data = request.get_json()
        app.logger.debug(f"Command UUID: {uuid}, Data: {request_data}")
        if request_data and "task" in request_data:  
            add_beacon_command_list(uuid, request_data["task"])
            app.logger.info(f"Command added for UUID: {uuid}")
            return jsonify({"status": "Command added"})
        else:
            app.logger.error("No data provided in POST request.")
            return jsonify({"error": "No data provided"}), 400

    elif request.method == 'GET':
        if request.args.get('history'):
            uuid = request.args.get('history')
            userID = request.args.get('history')
            history_data = []
            for j in range(len(beacon_commands["beacon_uuid"])):
                if beacon_commands["beacon_uuid"][j] == userID:
                    history_data.append({
                        "command_id": beacon_commands["command_uuid"][j],
                        "command": beacon_commands["command"][j],
                        "response": beacon_commands["command_output"][j]
                    })
            return jsonify({"history": history_data})
        else:
            # Handle GET requests without 'history' parameter
            beacons_grouped = {}
            # Loop through the beacons and group them by UUID
            for i in range(len(beacons["uuid"])):
                uuid = beacons["uuid"][i]
                beacons_grouped[uuid] = {
                    "address": [beacons["address"][i]],
                    "hostname": [beacons["hostname"][i]],
                    "operating_system": [beacons["operating_system"][i]],
                    "last_beacon": [beacons["last_beacon"][i]],
                    "next_beacon": [beacons["next_beacon"][i]],
                    "timer": [beacons["timer"][i]],
                    "jitter": [beacons["jitter"][i]]
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
    for i in range(len(beacons["uuid"])):
        if beacons["uuid"][i] == uuid:
            beacon_data = {
                "address": beacons["address"][i],
                "hostname": beacons["hostname"][i],
                "operating_system": beacons["operating_system"][i],
                "last_beacon": beacons["last_beacon"][i],
                "next_beacon": beacons["next_beacon"][i],
                "timer": beacons["timer"][i],
                "jitter": beacons["jitter"][i]
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
        for i in range(len(beacons["uuid"])):
            if beacons["uuid"][i] == uuid:
                beacon_data = {
                    "address": beacons["address"][i],
                    "hostname": beacons["hostname"][i],
                    "operating_system": beacons["operating_system"][i],
                    "last_beacon": beacons["last_beacon"][i],
                    "next_beacon": beacons["next_beacon"][i],
                    "timer": beacons["timer"][i],
                    "jitter": beacons["jitter"][i]
                }
                break
        if beacon_data:
            return render_template('beacon.html', beacon=beacon_data, uuid=uuid)
        else:
            return redirect('/')
    else:
        return redirect('/')
    
    
@app.route('/')
def index():
    response = make_response(render_template('index.html', beacons=beacons, commands=beacon_commands))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route('/favicon.ico')
def favicon():
    return "", 204
