from flask import Flask
from server.utils.logs import logger

class WebUIServer:
    def __init__(self, host, port, cert_path, key_path):
        self.host = host
        self.port = port
        self.cert_path = cert_path
        self.key_path = key_path
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'secret!'

    def start(self):
        logger.info("Starting Promethean Proxy WebUI server...")
        self.app.run(host=self.host, port=self.port, ssl_context=(self.cert_path, self.key_path))