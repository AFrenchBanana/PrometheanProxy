
import json
import ssl
import secrets 

from ..session.transfer import send_data, receive_data

class Client():
    def __init__(self, conn: ssl.socket, address: tuple, user: str, authenticated: bool):
        if not isinstance(conn, ssl.socket) or not isinstance(address, tuple) or not isinstance(user, str):
            raise ValueError("Invalid types for connection parameters")
        self.conn = conn
        self.address = address
        self.user = user
        self.is_authenticated = authenticated
        self.auth_key = self.generateAuthKey()

    def generateAuthKey(self):
        """
        Generates a unique authentication key for the connection.
        This could be a simple random string or a more complex token.
        """
        return secrets.token_hex(16)
    

    def auth_check(self, data: str):
        """
        pass in data recieved and it will validate there is an auth token that is valid for the session
        """
        try:
            payload = json.loads(data)
            if payload.get("authorization") == self.auth_key:
                return True
        except json.JSONDecodeError:
            pass
        return False

    def start(self):
        send_data(self.conn, json.dumps({
            "authorization": self.auth_key,
        }).encode('utf-8'))
        while True:
            data = receive_data(self.conn)
            if self.auth_check(data):
                print(f"Authorized data received from {self.user}: {data}")
            else:
                print(f"Unauthorized data received from {self.user}: {data}")
