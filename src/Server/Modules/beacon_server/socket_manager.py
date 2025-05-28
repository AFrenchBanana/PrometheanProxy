
from flask import Flask
from flask_socketio import SocketIO

# A minimal Flask app is required by Flask-SocketIO to handle WebSocket connections.
# This app will not serve any regular HTTP routes.
socket_flask_app = Flask(__name__)

# The single, shared SocketIO instance.
socketio = SocketIO(
    socket_flask_app,
    cors_allowed_origins="*",
    async_mode="threading"
)
