
import json
import ssl
import secrets 

from ..session.transfer import send_data, receive_data
from ..global_objects import beacon_list, sessions_list

class Client():
    def __init__(self, conn: ssl.socket, address: tuple, user: str, authenticated: bool):
        if not isinstance(conn, ssl.socket) or not isinstance(address, tuple) or not isinstance(user, str):
            raise ValueError("Invalid types for connection parameters")
        self.conn = conn
        self.address = address
        self.user = user
        self.is_authenticated = authenticated
        self.auth_key = self.generateAuthKey()
        self.available_commands = {"beacon": ["test"], "session": ["test2"]}

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
        emptyRecv = 0
        send_data(self.conn, json.dumps({
            "authorization": self.auth_key,
        }).encode('utf-8'))
        while True:
            if emptyRecv > 5:
                self.conn.close()
                break
            data = receive_data(self.conn)
            if data == b'':
                emptyRecv += 1
                continue
            print(f"Received data: {data}")
            if self.auth_check(data):
                try:
                    print("Valid auth token received")
                    command_data = json.loads(data)
                    command = command_data.get("command")
                    args = command_data.get("args", {})
                    def handle_status():
                        send_data(self.conn, json.dumps({"user": self.user, "authenticated": self.is_authenticated}).encode('utf-8'))
                    def handle_connections():
                        print("response")
                        send_data(self.conn, json.dumps({"response": self.get_active_connections()}).encode('utf-8'))
                    def available_commands():
                        send_data(self.conn, json.dumps({"response": self.list_commands(args)}).encode('utf-8'))
                    command_handlers = {
                        "status": handle_status,
                        "connections": handle_connections,
                        "commands": available_commands
                    }
                    handler = command_handlers.get(
                        command,
                        lambda: send_data(self.conn, json.dumps({"error": "Unknown command"}).encode('utf-8'))
                    )
                    handler()
                except Exception as e:
                    print(e)
                    send_data(self.conn, json.dumps({"error": "Invalid command format"}).encode('utf-8'))

    def get_active_connections(self):
        """
        Returns a list of active connections.
        """
        # This is a placeholder implementation. Replace with actual logic to retrieve active connections.
        beacons = []
        sessions = []
        for userID, beacon in beacon_list.items():
            beacons.append({
                "userID": userID,
                "uuid": getattr(beacon, "uuid", None),
                "address": getattr(beacon, "address", None),
                "hostname": getattr(beacon, "hostname", None),
                "operating_system": getattr(beacon, "operating_system", None),
                "last_beacon": getattr(beacon, "last_beacon", None),
                "next_beacon": getattr(beacon, "next_beacon", None),
                "timer": getattr(beacon, "timer", None),
                "jitter": getattr(beacon, "jitter", None),
            })
        for userID, session in sessions_list.items():
            sessions.append({
                "userID": userID,
                "address": getattr(session, "address", None),
                "hostname": getattr(session, "hostname", None),
                "operating_system": getattr(session, "operating_system", None),
                "mode": getattr(session, "mode", None),
                "load_modules": getattr(session, "load_modules", None),
            })
        return {"beacons": beacons, "sessions": sessions}

    def list_commands(self, arguments: dict):
        implant_uuid = arguments.get("uuid")
        for userID, beacon in beacon_list.items():
            beacon_uuid = getattr(beacon, "uuid", None) or userID
            if beacon_uuid == implant_uuid:
                mode = getattr(beacon, "mode", "beacon")
                return self.available_commands.get(mode, self.available_commands.get("beacon"))
        for userID, session in sessions_list.items():
            session_uuid = getattr(session, "uuid", None) or userID
            if session_uuid == implant_uuid:
                mode = getattr(session, "mode", "session")
                return self.available_commands.get(mode, self.available_commands.get("session"))
        return {"error": "Invalid UUID"}