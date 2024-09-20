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
from Modules.authentication import Authentication
from Modules.multi_handler_commands import MultiHandlerCommands
from PacketSniffing.PacketSniffer import PacketSniffer
from ServerDatabase.database import DatabaseClass
from Modules.global_objects import (
    send_data,
    receive_data,
    add_connection_list,
    connectionaddress,
    connectiondetails,
    execute_local_comands,
    config,
    tab_compeletion
)
from Modules.config_configuration import config_menu


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
        checks if TLS certificates are created
        in the location defined in config.toml.
        If these don't exist, a self signed key and certificate is made.
        """
        if not os.path.isfile(
            os.path.join(
                config['server']['TLSCertificateDir'],
                config['server']['TLSkey'])) and not os.path.isfile(
            os.path.join(
                config['server']['TLSCertificateDir'],
                config['server']['TLSCertificate'])):
            if os.path.isdir(config['server']['TLSCertificateDir']) is False:
                os.mkdir(config['server']['TLSCertificateDir'])
            os.system(
                "openssl req -x509 -newkey rsa:2048 -nodes -keyout " +
                os.path.join(
                    config['server']['TLSCertificateDir'],
                    config['server']['TLSkey']) + " -days 365 -out " +
                os.path.join(
                    config['server']['TLSCertificateDir'],
                    config['server']['TLSCertificate']) +
                "-subj '/CN=localhost'")
            print(
                colorama.Fore.GREEN +
                "TLS certificates created:" +
                os.path.join(
                    config['server']['TLSCertificateDir'],
                    config['server']['TLSkey']) and
                os.path.join(
                    config['server']['TLSCertificateDir'],
                    config['server']['TLSCertificate']))
        return

    def startsocket(self) -> None:
        """
        starts a TLS socket and threads the accept connection to allow
        multiple connections
        """
        global SSL_Socket, socket_clear
        self.address = (config['server']['listenaddress'],
                        config['server']['port'])
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=os.path.join(
                config['server']['TLSCertificateDir'],
                config['server']['TLSCertificate']),
            keyfile=os.path.join(
                config['server']['TLSCertificateDir'],
                config['server']['TLSkey']))
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
                # send if sniffer occurs
                send_data(conn, str(config['packetsniffer']['active']))
                if config['packetsniffer']['active']:
                    # send port number
                    send_data(conn, str(config['packetsniffer']['port']))
                add_connection_list(conn, r_address, hostname)
                threadDB.insert_entry(
                    "Addresses", f'"{
                        r_address[0]}", "{
                        r_address[1]}", "{hostname}", "{
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
            else:
                conn.close()

    def multi_handler(self, config: dict) -> None:
        print(
            colorama.Fore.YELLOW +
            f"Awaiting connection on port {self.address[0]}:{self.address[1]}")
        if config['packetsniffer']['active']:
            print(colorama.Back.GREEN,
                  "PacketSniffing active on port",
                  config['packetsniffer']['port'])
        while True:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(lambda text,
                                   state: tab_compeletion(text,
                                                          state,
                                                          ["list",
                                                           "sessions",
                                                           "close",
                                                           "closeall",
                                                           "hashfiles",
                                                           "config",
                                                           "help",
                                                           "exit",
                                                           "config"]))
            command = input("MultiHandler: ").lower()
            if command == "exit":  # closes the server down
                print(colorama.Fore.RED + "Closing connections")
                break  # exits the multihandler
            try:
                if command == "list":
                    self.multihandlercommands.listconnections(
                        connectionaddress)
                elif command == "sessions":
                    self.multihandlercommands.sessionconnect(
                        connectiondetails, connectionaddress)
                elif command == "close":
                    self.multihandlercommands.close_from_multihandler(
                        connectiondetails, connectionaddress)
                elif command == "closeall":
                    self.multihandlercommands.close_all_connections(
                        connectiondetails, connectionaddress)
                elif command == "hashfiles":
                    self.multihandlercommands.localDatabaseHash()
                elif command == "config":
                    config_menu()
                elif not execute_local_comands(command):
                    # if this fails print the help menu text in the config
                    print(config['MultiHandlerCommands']['help'])
            except (KeyError, SyntaxError, AttributeError):
                # if this fails print the help menu text in the config
                print(config['MultiHandlerCommands']['help'])
        return
