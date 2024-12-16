from flask import Flask, render_template, jsonify
from Modules.global_objects import beacons, beacon_commands
import logging

app = Flask(__name__)
log = logging.getLogger('werkzeug')
app.logger.setLevel(logging.ERROR)
log.setLevel(logging.ERROR)


@app.route('/api/beacons')
def api_beacons():
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

@app.route('/')
def index():
    return render_template('index.html', beacons=beacons, commands=beacon_commands)

