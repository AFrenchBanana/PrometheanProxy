import socket
import ssl
import json

def connect_to_server():
    server_address = ('localhost', 2001)
    context = ssl.create_default_context()
    # If using self-signed certs, you may want to disable cert verification for testing:
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection(server_address) as sock:
        with context.wrap_socket(sock, server_hostname='localhost') as ssock:
            print("Connected to server with SSL")
            # Example: send a message
            ssock.sendall(json.dumps({
                "username": "testuser", 
            }).encode('utf-8'))


if __name__ == "__main__":
    connect_to_server()