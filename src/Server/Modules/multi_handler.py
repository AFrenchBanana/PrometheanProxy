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

from datetime import datetime
from .authentication import Authentication
from .multi_handler_commands import MultiHandlerCommands
from PacketSniffing.PacketSniffer import PacketSniffer
from ServerDatabase.database import DatabaseClass
from .global_objects import (
    send_data,
    receive_data,
    add_connection_list,
    sessions_list,
    execute_local_commands,
    config,
    tab_completion,
    beacon_list,
)
from Modules.config_configuration import config_menu, beacon_config_menu


class MultiHandler:
    def __init__(self) -> None:
        """
        main function that starts the socket server, threads the
        socket.start() as a daemon to allow multiple connections,
        it starts the database for the main thread
        it then runs the multihandler function
        """
        self.multihandlercommands = MultiHandlerCommands()
        self.Authentication = Authentication()
        self.database = DatabaseClass()
        colorama.init(autoreset=True)
        if config['packetsniffer']['active']:
            sniffer = PacketSniffer()
            sniffer.start_raw_socket()

    def create_certificate(self) -> None:
        """
        Checks if TLS certificates are created in the location
        defined in config.
        If these don't exist, a self-signed key and certificate is made.
        """
        cert_dir = config['server']['TLSCertificateDir']
        tls_key = config['server']['TLSkey']
        tls_cert = config['server']['TLSCertificate']

        key_path = os.path.join(cert_dir, tls_key)
        cert_path = os.path.join(cert_dir, tls_cert)

        if not os.path.isfile(key_path) and not os.path.isfile(cert_path):
            if not os.path.isdir(cert_dir):
                os.mkdir(cert_dir)
            os.system(
                "openssl req -x509 -newkey rsa:2048 -nodes -keyout " +
                f"{key_path} -days 365 -out {cert_path} -subj " +
                "'/CN=localhost'"
            )
            print(colorama.Fore.GREEN +
                  "TLS certificates created: " +
                  f"{cert_dir}{tls_key} and {cert_dir}{tls_cert}")

    def startsocket(self) -> None:
        """
        starts a TLS socket and threads the accept connection to allow
        multiple connections
        """
        global SSL_Socket, socket_clear
        self.address = (config['server']['listenaddress'],
                        config['server']['port'])
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        cert_dir = config['server']['TLSCertificateDir']
        tls_key = config['server']['TLSkey']
        tls_cert = config['server']['TLSCertificate']
        context.load_cert_chain(
            certfile=os.path.join(cert_dir, tls_cert),
            keyfile=os.path.join(cert_dir, tls_key))
        socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        SSL_Socket = context.wrap_socket(socket_clear, server_side=True)
        # tries to bind the socket to an address
        try:
            SSL_Socket.bind(self.address)
        except OSError:  # error incase socket is already being used
            print(colorama.Fore.RED +
                  f"{self.address[0]}:{self.address[1]} already in use")
            sys.exit(1)
        SSL_Socket.listen()
        listenerthread = threading.Thread(
            target=self.accept_connection,
            args=())
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
        threadDB = DatabaseClass()
        while True:
            conn, r_address = SSL_Socket.accept()
            send_data(conn, self.Authentication.get_authentication_string())
            if (self.Authentication.test_auth(
                    receive_data(conn), r_address[1])):
                hostname = receive_data(conn)
                data = receive_data(conn)  # OS and User ID
                try:
                    OS, id = data.split(",")
                except ValueError:
                    OS = data
                    id = None
                send_data(conn, str(config['packetsniffer']['active']))
                if config['packetsniffer']['active']:
                    # send port number
                    send_data(conn, str(config['packetsniffer']['port']))
                add_connection_list(conn, r_address, hostname,
                                    OS, id, "session")
                threadDB.insert_entry(
                    "Addresses",
                    f'"{r_address[0]}", "{r_address[1]}", "{hostname}", ' +
                    f'"{data[0]}", ' +
                    f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
            else:
                conn.close()

    def multi_handler(self, config: dict) -> None:
        try:
            print(
                colorama.Fore.YELLOW +
                f"Awaiting connection on port {self.address[0]}:"
                f"{self.address[1]}")
            if config['packetsniffer']['active']:
                print(colorama.Back.GREEN,
                      "PacketSniffing active on port",
                      config['packetsniffer']['port'])
            while True:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state:
                        tab_completion(text,
                                       state, ["list", "sessions", "beacons",
                                               "close", "closeall",
                                               "configbeacon",
                                               "command", "hashfiles",
                                               "config", "help", "exit",]))
                command = input("MultiHandler: ").lower()
                if command == "exit":  # closes the server down
                    print(colorama.Fore.RED + "Closing connections")
                    break  # exits the multihandler

                def handle_sessions():
                    if len(sessions_list) == 0:
                        print(colorama.Fore.RED + "No sessions connected")
                    else:
                        self.multihandlercommands.sessionconnect()

                def handle_beacons():
                    if len(beacon_list) == 0:
                        print(colorama.Fore.RED + "No beacons connected")
                    elif len(beacon_list) > 1:
                        index = int(input("Enter the index of the beacon: "))
                        try:
                            beacon = list(beacon_list.values())[index]                       
                            self.multihandlercommands.use_beacon(
                                beacon.uuid,
                                beacon.address
                            )
                                
                        except IndexError:
                            print(colorama.Fore.RED + "Index out of range")
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
                    "configBeacon": beacon_config_menu
                }

                try:
                    handler = command_handlers.get(command)
                    if handler:
                        handler()
                    else:
                        if not execute_local_commands(command):
                            print(config['MultiHandlerCommands']['help'])
                except (KeyError, SyntaxError, AttributeError) as e:
                    print(e)
        except KeyboardInterrupt:
            print(colorama.Fore.RED + "\nUse exit next time")
        return
