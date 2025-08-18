import socket
import threading
import colorama
import ssl
import os
import json
from ..global_objects import logger, multiplayer_connections

from .mp_client import Client
from ..session.transfer import send_data, receive_data, perform_ecdh_handshake


class MP_Socket:
    """
    This module handles the creation and management of a secure socket server for multiplayer connections.
    It uses SSL for secure communication and listens for incoming connections on a specified port.
    """
    def __init__(self, config):
        self.config = config
        self.socket = None
        self.sslSocket = None
        self.port = config['server']['multiplayerPort']
        if not (isinstance(self.port, int) and 1 <= self.port <= 65535):
            logger.error(f"Invalid port number: {self.port}. Must be between 1 and 65535.")
            raise ValueError("Invalid port number")        


    def start(self):
        try:
            logger.info("Starting socket server")
            self.address = (self.config['server']['multiplayerListenAddress'],
                            self.config['server']['multiplayerPort'])
            logger.debug(f"Socket address: {self.address}")
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            logger.debug("Creating SSL context")
            cert_dir = os.path.expanduser(f"~/.PrometheanProxy/{self.config['server']['TLSCertificateDir']}")
            tls_key = self.config['server']['TLSkey']
            tls_cert = self.config['server']['TLSCertificate']
            logger.debug(f"Certificate directory: {cert_dir}, Key: {tls_key}, Cert: {tls_cert}")
            context.load_cert_chain(
                certfile=os.path.join(cert_dir, tls_cert),
                keyfile=os.path.join(cert_dir, tls_key))
            logger.debug("SSL context loaded with certificate and key")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            logger.debug("Creating clear socket")
            self.sslSocket = context.wrap_socket(self.socket, server_side=True)
            logger.debug("Wrapping socket with SSL context")
        except FileNotFoundError:
            logger.error("TLS certificate or key file not found")
            raise FileNotFoundError("TLS certificate or key file not found")
        except ssl.SSLError as e:
            logger.critical(f"SSL error: {e}")
            raise ssl.SSLError(f"SSL error: {e}")
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            raise Exception(f"Unexpected error: {e}")
        try:
            self.sslSocket.bind(self.address)
            logger.info(f"Socket bound to {self.address[0]}:{self.address[1]}")
        except OSError:  # error incase socket is already being used
            logger.error(f"Socket {self.address[0]}:{self.address[1]} already in use")
            print(colorama.Fore.RED +
                  f"{self.address[0]}:{self.address[1]} already in use")
            logger.critical("Exiting due to socket error")
        self.sslSocket.listen()
        logger.info(f"Socket listening on {self.address[0]}:{self.address[1]}")
        logger.debug("Starting listener thread for accepting connections")
        listenerthread = threading.Thread(
            target=self.accept_connection, 
            args=())
        logger.debug("Starting listener thread for accepting connections")
        listenerthread.daemon = True
        listenerthread.start()
        return

    def accept_connection(self) -> None:
        """
        Function that listens for connections and handles them, by calling
        connection_list() to make them referencable. The database is
        initalised and then when a new connection is recieved the details
        are inserted to the database table addresses
        Ideally run as a deamon thread to allow any connections to input.
        """
        # threadDB = DatabaseClass(self.config)
        logger.info("Accepting connections on socket")
        while True:
            conn, r_address = self.sslSocket.accept()
            # Establish app-layer ECDH key over SSL, then proceed
            try:
                perform_ecdh_handshake(conn, is_server=True)
            except Exception as e:
                logger.error(f"ECDH handshake failed from {r_address}: {e}")
                try:
                    conn.close()
                finally:
                    continue
            data = receive_data(conn)
            try:
                userinfo = json.loads(data)
            except Exception as e:
                logger.warning(f"Failed to decode JSON from {r_address}: {e}")
                conn.close()
                continue
            logger.info(f"Connection accepted from {r_address}")
            if not userinfo.get("username") or not userinfo.get("password"):
                logger.warning("Received connection with empty username or password")
                conn.close()
                continue
            else:
                logger.info(f"Received connection from user: {userinfo['username']}")
            username = userinfo.get("username")
            password = userinfo.get("password")
            if username in multiplayer_connections or username == self.current_user:
                logger.warning(f"User {username} is already logged in from another connection")
                print(colorama.Fore.YELLOW, f"User {username} is already logged in from another connection")
                send_data(conn, "User already logged in")
                conn.close()
                continue

            if self.authenticate_user(username, password):
                logger.info(f"User {username} authenticated successfully from {r_address}")
                print(colorama.Fore.GREEN, f"User {username} authenticated successfully from {r_address}")
                mp_client = Client(conn, r_address, username, True)
                multiplayer_connections[username] = mp_client
                client_thread = threading.Thread(target=mp_client.start, args=())
                client_thread.daemon = True
                client_thread.start()
                continue

            else:
                logger.warning(f"Authentication failed for user {username} from {r_address}")
                print(colorama.Fore.RED, f"Authentication failed for user {username} from {r_address}")
                send_data(conn, "Authentication failed")
                conn.close()
                continue
            