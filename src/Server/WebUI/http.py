from flask import Flask, render_template, jsonify, request, redirect
from flask_socketio import SocketIO
from Modules.global_objects import beacons, beacon_commands
import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
log = logging.getLogger('werkzeug')
app.logger.setLevel(logging.ERROR)
log.setLevel(logging.ERROR)


@app.route('/api/v1/beacons')
def api_beacons():
    if request.remote_addr != '127.0.0.1':
        return jsonify({"error": "Access denied"}), 403

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

    return jsonify({"beacons": beacons_grouped})

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

@app.route('/')
def index():
    return render_template('index.html', beacons=beacons, commands=beacon_commands)


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

@app.route('/favicon.ico')
def favicon():
    return "", 204
