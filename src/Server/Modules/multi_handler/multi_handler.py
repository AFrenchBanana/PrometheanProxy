"""multi handler file
manages the intial server socket connection, encryption and authentication.
Checks if SSL certificates are made and can create them if not
Threading to accept multiple connections and start a packet
sniffer on each thread if needed.
Also has the intital multi handler menu the users interacts with.
"""

import socket
import ssl
import threading
import os
import sys
import colorama
import readline
import json

from datetime import datetime
from ..utils.authentication import Authentication
from .multi_handler_commands import MultiHandlerCommands
from PacketSniffing.PacketSniffer import PacketSniffer
from ServerDatabase.database import DatabaseClass
from ..session.session import add_connection_list, receive_data, send_data
from ..global_objects import (
    sessions_list,
    beacon_list,
    execute_local_commands,
    config,
    tab_completion,
    logger
)
from Modules.utils.config_configuration import config_menu, beacon_config_menu


class MultiHandler:
    def __init__(self) -> None:
        """
        main function that starts the socket server, threads the
        socket.start() as a daemon to allow multiple connections,
        it starts the database for the main thread
        it then runs the multihandler function
        """
        logger.info("Starting MultiHandler")
        self.multihandlercommands = MultiHandlerCommands(config)
        self.Authentication = Authentication()
        self.database = DatabaseClass(config)
        colorama.init(autoreset=True)
        if config['packetsniffer']['active']:
            sniffer = PacketSniffer()
            sniffer.start_raw_socket()
            logger.info("PacketSniffer started")

    def create_certificate(self) -> None:
        """
        Checks if TLS certificates are created in the location
        defined in config.
        If these don't exist, a self-signed key and certificate is made.
        """
        logger.info("Checking for TLS certificates")
        cert_dir = os.path.expanduser(f"~/.PrometheanProxy/{config['server']['TLSCertificateDir']}")
        tls_key = config['server']['TLSkey']
        tls_cert = config['server']['TLSCertificate']

        key_path = os.path.join(cert_dir, tls_key)
        cert_path = os.path.join(cert_dir, tls_cert)
        logger.debug(f"Key path: {key_path}, Cert path: {cert_path}")

        if not os.path.isfile(key_path) and not os.path.isfile(cert_path):
            logger.info("TLS certificates not found, creating new ones")
            if not os.path.isdir(cert_dir):
                logger.debug(f"Creating directory for TLS certificates: {cert_dir}")
                os.mkdir(cert_dir)
            os.system(
                "openssl req -x509 -newkey rsa:2048 -nodes -keyout " +
                f"{key_path} -days 365 -out {cert_path} -subj " +
                "'/CN=localhost'"
            )
            logger.info("TLS certificates created successfully")
            print(colorama.Fore.GREEN +
                  "TLS certificates created: " +
                  f"{cert_dir}{tls_key} and {cert_dir}{tls_cert}")

    def startsocket(self) -> None:
        """
        starts a TLS socket and threads the accept connection to allow
        multiple connections
        """
        try:
            logger.info("Starting socket server")
            global SSL_Socket, socket_clear
            self.address = (config['server']['listenaddress'],
                            config['server']['port'])
            logger.debug(f"Socket address: {self.address}")
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            logger.debug("Creating SSL context")
            cert_dir = os.path.expanduser(f"~/.PrometheanProxy/{config['server']['TLSCertificateDir']}")
            tls_key = config['server']['TLSkey']
            tls_cert = config['server']['TLSCertificate']
            logger.debug(f"Certificate directory: {cert_dir}, Key: {tls_key}, Cert: {tls_cert}")
            context.load_cert_chain(
                certfile=os.path.join(cert_dir, tls_cert),
                keyfile=os.path.join(cert_dir, tls_key))
            logger.debug("SSL context loaded with certificate and key")
            socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            logger.debug("Creating clear socket")
            SSL_Socket = context.wrap_socket(socket_clear, server_side=True)
            logger.debug("Wrapping socket with SSL context")
        except FileNotFoundError:
            logger.error("TLS certificate or key file not found")
            sys.exit(
                colorama.Fore.RED +
                "TLS certificate or key file not found. " +
                "Please run the server with --create-certificate to generate them.")
        except ssl.SSLError as e:
            logger.critical(f"SSL error: {e}")
            print(colorama.Fore.RED + "SSL error: " + str(e))
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            print(colorama.Fore.RED + "Unexpected error: " + str(e))
            sys.exit(1)
        try:
            SSL_Socket.bind(self.address)
            logger.info(f"Socket bound to {self.address[0]}:{self.address[1]}")
        except OSError:  # error incase socket is already being used
            logger.error(f"Socket {self.address[0]}:{self.address[1]} already in use")
            print(colorama.Fore.RED +
                  f"{self.address[0]}:{self.address[1]} already in use")
            logger.critical("Exiting due to socket error")
            sys.exit(1)
        SSL_Socket.listen()
        logger.info(f"Socket listening on {self.address[0]}:{self.address[1]}")
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
        threadDB = DatabaseClass(config)
        logger.info("Accepting connections on socket")
        while True:
            conn, r_address = SSL_Socket.accept()
            logger.info(f"Connection accepted from {r_address[0]}:{r_address[1]}")
            send_data(conn, self.Authentication.get_authentication_string())
            logger.debug("Sent authentication string to client")
            if (self.Authentication.test_auth(
                    receive_data(conn))):
                logger.info(f"Authentication successful for {r_address[0]}:{r_address[1]}")
                data = receive_data(conn)
                logger.debug(f"Received data from client: {data}")
                try:
                    data_json = json.loads(data)
                    hostname = data_json.get("Hostname")
                    os = data_json.get("OS")
                    id = data_json.get("ID")
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Failed to decode JSON data: {e}")
                    os = None
                    id = None
                logger.debug(f"Received hostname from client: {hostname}")
                send_data(conn, str(config['packetsniffer']['active']))
                logger.debug(f"OS: {os}, ID: {id}")
                if config['packetsniffer']['active']:
                    # send port number
                    send_data(conn, str(config['packetsniffer']['port']))
                    logger.debug("Sent packet sniffer port to client")
                add_connection_list(conn, r_address, hostname,
                                    os, id, "session", config)
                logger.info(f"Added connection to sessions list: {hostname} ({os})")
                threadDB.insert_entry(
                    "Addresses",
                    f'"{r_address[0]}", "{r_address[1]}", "{hostname}", ' +
                    f'"{data[0]}", ' +
                    f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
            else:
                conn.close()

    def multi_handler(self, config: dict) -> None:
        logger.info("Starting MultiHandler menu")
        try:
            print(
                colorama.Fore.YELLOW +
                f"Awaiting connection on port {self.address[0]}:"
                f"{self.address[1]}")
            if config['packetsniffer']['active']:
                print(colorama.Back.GREEN,
                      "PacketSniffing active on port",
                      config['packetsniffer']['port'])
                logger.info("PacketSniffing is active")
            while True:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state:
                        tab_completion(text,
                                       state, ["list", "sessions", "beacons",
                                               "close", "closeall",
                                               "configbeacon",
                                               "command", "hashfiles",
                                               "config", "configBeacon", "logs", "help", "exit",]))
                command = input("MultiHandler: ").lower()
                logger.debug(f"Received command: {command}")
                if command == "exit":  # closes the server down
                    print(colorama.Fore.RED + "Closing connections")
                    break  # exits the multihandler

                def handle_sessions():
                    logger.debug("Handling sessions command")
                    if len(sessions_list) == 0:
                        print(colorama.Fore.RED + "No sessions connected")
                    else:
                        self.multihandlercommands.sessionconnect()

                def handle_beacons():
                    logger.debug("Handling beacons command")
                    if len(beacon_list) == 0:
                        print(colorama.Fore.RED + "No beacons connected")
                        logger.warning("No beacons connected")
                    elif len(beacon_list) > 1:
                        index = int(input("Enter the index of the beacon: "))
                        logger.debug(f"Selected beacon index: {index}")
                        try:
                            beacon = list(beacon_list.values())[index]
                            self.multihandlercommands.use_beacon(
                                beacon.uuid,
                                beacon.address
                            )
                            logger.info(f"Using beacon {beacon.uuid} at {beacon.address}")

                        except IndexError:
                            print(colorama.Fore.RED + "Index out of range")
                            logger.error("Index out of range for beacon selection")
                    else:
                        beacon = list(beacon_list.values())[0]
                        self.multihandlercommands.use_beacon(
                            beacon.uuid,
                            beacon.address
                        )

                command_handlers = {
                    "list": self.multihandlercommands.listconnections,
                    "sessions": handle_sessions,
                    "beacons": handle_beacons,
                    "close": lambda:
                        self.multihandlercommands.close_from_multihandler(),
                    "closeall": lambda:
                        self.multihandlercommands.close_all_connections(),
                    "hashfiles": self.multihandlercommands.localDatabaseHash,
                    "config": config_menu,
                    "configBeacon": beacon_config_menu,
                    "logs": self.multihandlercommands.view_logs,
                }

                try:
                    logger.debug(f"Executing command: {command}")
                    handler = command_handlers.get(command)
                    if handler:
                        handler()
                    else:
                        logger.error(f"Unknown command: {command}")
                        if not execute_local_commands(command):
                            print(config['MultiHandlerCommands']['help'])
                except (KeyError, SyntaxError, AttributeError) as e:
                    logger.error(f"Error executing command: {e}")
                    print(e)
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt received, exiting MultiHandler")
            print(colorama.Fore.RED + "\nUse exit next time")
        return
