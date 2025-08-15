import socket
import ssl
import json

from transfer import send_data, receive_data

class RemoteServer:
    def __init__(self):
        self.address = ('localhost', 2003)
        self.current_user = None
        self.username = "test"
        self.password = "test"

        self.sslSocket =  self.connect_to_server()
        self.auth_key = self.authenticate()
        self.current_user = self.username if self.auth_key else None

        self.get_current_connections()

    def connect_to_server(self) -> (ssl.SSLSocket):
        server_address = ('localhost', 2003)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            sock = socket.create_connection(server_address)
            ssock = context.wrap_socket(sock, server_hostname='localhost')
            return ssock
        except Exception as e:
            print(f"Failed to connect to {server_address}: {e}")
            return None

    def authenticate(self):
        if self.sslSocket:
            send_data(self.sslSocket, json.dumps({
                "username": self.username,
                "password": self.password
            }).encode('utf-8'))
            response = receive_data(self.sslSocket)
            print(response)
            if json.loads(response).get("authorization"):
                print(f"Authentication successful: {response}")
                return json.loads(response).get("authorization")
            else:
                print(f"Authentication failed: {response}")
                return ""
        else:
            print("Not connected to server")
            return ""

    def get_current_connections(self):
        if self.sslSocket:
            send_data(self.sslSocket, json.dumps({
                "command": "get_connections",
                "authorization": self.auth_key
            }).encode('utf-8'))
            response = receive_data(self.sslSocket)
            print(f"Current connections: {response}")
        else:
            print("Not connected to server")

if __name__ == "__main__":
    remote_server = RemoteServer()
    