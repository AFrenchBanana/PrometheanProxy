# ============================================================================
# Multi Handler Module
# ============================================================================
# This module manages multiple client sessions and beacon connections,
# providing a unified command interface for interacting with connected clients.
# ============================================================================

# Standard Library Imports
import ast
import json
import os
import readline
import secrets
import socket
import ssl
import sys
import threading
import traceback
import uuid
from datetime import datetime, time

# Third-Party Imports
import colorama
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI, HTML

# Local Module Imports
from ..utils.authentication import Authentication
from .multi_handler_commands import MultiHandlerCommands
from PacketSniffing.PacketSniffer import PacketSniffer
from ServerDatabase.database import DatabaseClass
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
from Modules.utils.console import (
    cprint, warn, error as c_error, success, info, colorize
)
from Modules.utils.ui_manager import (
    get_ui_manager,
    log_connection_event,
    update_connection_stats
)


# ============================================================================
# MultiHandler Class
# ============================================================================


class MultiHandler:
    """
    Manages multiple client sessions and beacon connections.
    
    This class serves as the main controller for handling multiple simultaneous
    connections, including both interactive sessions and asynchronous beacons.
    It provides initialization, socket management, authentication, and command
    interface functionality.
    
    Attributes:
        multihandlercommands: Command handler instance for user commands
        Authentication: Authentication handler for client verification
        database: Database instance for storing connection and command data
        isMultiplayer: Flag indicating if multiplayer mode is enabled
        multiplayer: MultiPlayer instance if multiplayer mode is active
        address: Tuple of (host, port) for the listening socket
    """

    def __init__(self) -> None:
        """Initialize the MultiHandler with all necessary components."""
        from Modules import global_objects
        
        logger.info("Starting MultiHandler")
        
        # Initialize UI Manager
        self.ui_manager = get_ui_manager()
        self.prompt_session = PromptSession()
        
        # Initialize core components
        self.multihandlercommands = MultiHandlerCommands(config)
        self.Authentication = Authentication()
        self.database = DatabaseClass(config, "command_database")
        global_objects.command_database = self.database
        
        # Set up security certificates and keys
        self.create_certificate()
        self.create_hmac()
        
        # Load existing implants from database
        self.load_db_implants()
        
        # Initialize colorama for colored terminal output
        colorama.init(autoreset=True)
        
        # Initialize packet sniffer if enabled in config
        if config['packetsniffer']['active']:
            sniffer = PacketSniffer()
            sniffer.start_raw_socket()
            logger.info("PacketSniffer started")
            log_connection_event("info", "PacketSniffer started")

        # Initialize multiplayer mode if enabled
        self.isMultiplayer = False
        try:
            if config['multiplayer']['multiplayerEnabled']:
                self.isMultiplayer = True
                self.multiplayer = MultiPlayer(config)
                self.multihandlercommands = MultiHandlerCommands(config)
                success("Multiplayer mode enabled")
                logger.info("Server: Multiplayer mode enabled")
                log_connection_event("info", "Multiplayer mode enabled")
                threading.Thread(
                    target=self.multiplayer.start(),
                    args=(config,),
                    daemon=True
                ).start()
        except KeyError as e:
            warn("Multiplayer configuration not found, continuing in singleplayer mode")
            traceback.print_exc()
            warn(str(e))
            logger.info("Server: Continuing in singleplayer mode")

    # ========================================================================
    # Database Loading Methods
    # ========================================================================

    def load_db_implants(self):
        """
        Load implants from the database into memory.
        
        Retrieves stored beacons and sessions from the database and recreates
        them in the active connection lists. This allows persistence of
        connections across server restarts.
        """
        logger.info("Loading implants from database")
        try:
            # ----------------------------------------------------------------
            # Load Beacons from Database
            # ----------------------------------------------------------------
            # Schema: uuid, IP, Hostname, OS, LastBeacon, NextBeacon,
            #         Timer, Jitter, modules
            beacons = self.database.fetch_all("beacons")
            if beacons:
                for beacon in beacons:
                    try:
                        # Parse beacon data from database row
                        uuid_val = beacon[0]
                        ip = beacon[1]
                        hostname = beacon[2]
                        os_val = beacon[3]
                        
                        # Handle last_beacon time conversion
                        try:
                            last_beacon = beacon[4]
                        except (ValueError, TypeError):
                            last_beacon = float(beacon[4]) if beacon[4] else 0.0
                        
                        # Parse timing information
                        timer = float(beacon[6]) if beacon[6] else 0.0
                        jitter = float(beacon[7]) if beacon[7] else 0.0
                        
                        # Parse modules list
                        modules_data = beacon[8]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = modules_data if isinstance(modules_data, list) else []
                        
                        # Add beacon to active list
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

            # ----------------------------------------------------------------
            # Load Sessions from Database
            # ----------------------------------------------------------------
            # Schema: address, details, hostname, operating_system,
            #         mode, modules
            sessions = self.database.fetch_all("sessions")
            if sessions:
                for session in sessions:
                    try:
                        # Parse address data
                        address_data = session[0]
                        if isinstance(address_data, str):
                            try:
                                address = ast.literal_eval(address_data)
                            except (ValueError, SyntaxError):
                                address = (address_data, 0)
                        else:
                            address = address_data

                        # Parse session details
                        details = session[1]
                        hostname = session[2]
                        operating_system = session[3]
                        mode = session[4]
                        
                        # Parse modules list
                        modules_data = session[5]
                        if isinstance(modules_data, str):
                            try:
                                modules = ast.literal_eval(modules_data)
                            except (ValueError, SyntaxError):
                                modules = []
                        else:
                            modules = modules_data if isinstance(modules_data, list) else []

                        # Generate user ID for session
                        user_id = str(uuid.uuid4())
                        
                        # Add session to active list
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

    # ========================================================================
    # Security Configuration Methods
    # ========================================================================

    def create_hmac(self):
        """
        Create or verify HMAC authentication key.
        
        Checks if an HMAC key exists in the configured location. If not found,
        generates a new 32-byte (64 hex character) key for client authentication.
        The key file is created with restricted permissions (0o600) for security.
        """
        logger.info("Checking for HMAC key")
        cert_dir = os.path.expanduser(config['server']['TLSCertificateDir'])
        hmac_key_path = os.path.join(cert_dir, "hmac.key")
        logger.debug(f"HMAC key path: {hmac_key_path}")

        if not os.path.isfile(hmac_key_path):
            logger.info("HMAC key not found, creating new one")
            if not os.path.isdir(cert_dir):
                logger.debug(f"Creating directory for HMAC key: {cert_dir}")
            
            # Generate a 32-byte (64 hex chars) key
            try:
                key = secrets.token_hex(32)
                with open(hmac_key_path, "w") as f:
                    f.write(key)
                
                # Set file permissions to owner-only read/write
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
        Create or verify TLS certificates for secure communication.
        
        Checks if TLS certificates exist in the configured location. If not found,
        generates new self-signed TLS certificates using OpenSSL for secure
        client-server communication.
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
            
            # Generate self-signed certificate using OpenSSL
            os.system(
                "openssl req -x509 -newkey rsa:2048 -nodes -keyout " +
                f"{key_path} -days 365 -out {cert_path} -subj " +
                "'/CN=localhost'"
            )
            logger.info("TLS certificates created successfully")
            cprint(
                "TLS certificates created: " +
                f"{cert_dir}{tls_key} and {cert_dir}{tls_cert}",
                fg="green"
            )

    # ========================================================================
    # Socket Server Methods
    # ========================================================================

    def startsocket(self) -> None:
        """
        Initialize and start the SSL socket server.
        
        Creates an SSL context, loads certificates, binds to the configured
        address and port, and begins listening for incoming connections.
        Starts a daemon thread to accept new connections.
        """
        try:
            logger.info("Starting socket server")
            global SSL_Socket, socket_clear
            
            # Get listening configuration from config
            self.address = (
                config['server']['listenaddress'],
                config['server']['port']
            )
            logger.debug(f"Socket address: {self.address}")
            
            # Create SSL context for secure communication
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            logger.debug("Creating SSL context")
            
            # Load TLS certificates
            cert_dir = os.path.expanduser(config['server']['TLSCertificateDir'])
            tls_key = config['server']['TLSkey']
            tls_cert = config['server']['TLSCertificate']
            logger.debug(
                f"Certificate directory: {cert_dir}, Key: {tls_key}, Cert: {tls_cert}"
            )
            context.load_cert_chain(
                certfile=os.path.join(cert_dir, tls_cert),
                keyfile=os.path.join(cert_dir, tls_key)
            )
            logger.debug("SSL context loaded with certificate and key")
            
            # Create and configure socket
            socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            socket_clear.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logger.debug("Creating clear socket")
            
            # Wrap socket with SSL context
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
        
        # Bind socket to address and start listening
        try:
            SSL_Socket.bind(self.address)
            logger.info(f"Socket bound to {self.address[0]}:{self.address[1]}")
        except OSError:
            logger.error(f"Socket {self.address[0]}:{self.address[1]} already in use")
            c_error(f"{self.address[0]}:{self.address[1]} already in use")
            logger.critical("Exiting due to socket error")
            sys.exit(1)
        
        SSL_Socket.listen()
        logger.info(f"Socket listening on {self.address[0]}:{self.address[1]}")
        
        # Start connection accept thread
        listenerthread = threading.Thread(
            target=self.accept_connection,
            args=()
        )
        logger.debug("Starting listener thread for accepting connections")
        listenerthread.daemon = True
        listenerthread.start()

    def accept_connection(self) -> None:
        """
        Accept and authenticate incoming client connections.
        
        Continuously listens for new connections, performs authentication,
        and adds authenticated clients to the appropriate session list.
        Runs in a daemon thread started by startsocket().
        """
        threadDB = DatabaseClass(config, "command_database")
        logger.info("Accepting connections on socket")
        
        while True:
            conn, r_address = SSL_Socket.accept()
            logger.info(f"Connection accepted from {r_address[0]}:{r_address[1]}")
            
            # Send authentication challenge
            send_data(conn, self.Authentication.get_authentication_string())
            logger.debug("Sent authentication string to client")
            
            # Verify authentication response
            if (self.Authentication.test_auth(receive_data(conn))):
                logger.info(
                    f"Authentication successful for {r_address[0]}:{r_address[1]}"
                )
                
                # Receive client information
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
                
                # Send packet sniffer configuration
                send_data(conn, str(config['packetsniffer']['active']))
                logger.debug(f"OS: {os}, ID: {id}")
                if config['packetsniffer']['active']:
                    send_data(conn, str(config['packetsniffer']['port']))
                    logger.debug("Sent packet sniffer port to client")
                
                # Add connection to sessions list
                add_connection_list(
                    conn, r_address, hostname,
                    os, id, "session", [], config
                )
                logger.info(f"Added connection to sessions list: {hostname} ({os})")
                
                # Log connection to database
                threadDB.insert_entry(
                    "Addresses",
                    f'"{r_address[0]}", "{r_address[1]}", "{hostname}", ' +
                    f'"{data[0]}", ' +
                    f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"'
                )
            else:
                conn.close()

    # ========================================================================
    # Command Interface Methods
    # ========================================================================

    def multi_handler(self, config: dict) -> None:
        """
        Main command interface loop for user interaction.
        
        Provides an interactive command prompt where operators can manage
        sessions, beacons, and server configuration. Handles command routing
        and execution.
        
        Args:
            config: Configuration dictionary containing server settings
        """
        logger.info("Starting MultiHandler menu")
        
        # Start the UI display
        self.ui_manager.start_display()
        
        # Update initial stats
        update_connection_stats(len(sessions_list), len(beacon_list))
        
        # Log initial server start
        log_connection_event("info", f"Server listening on {self.address[0]}:{self.address[1]}")
        
        try:
            info(f"Awaiting connection on port {self.address[0]}:{self.address[1]}")
            
            if config['packetsniffer']['active']:
                info(f"PacketSniffing active on port {config['packetsniffer']['port']}")
                logger.info("PacketSniffing is active")
            
            # Main command loop
            # Configure tab completion
            available_commands = [
                "list", "sessions", "beacons",
                "close", "closeall",
                "users" if self.isMultiplayer else None,
                "configbeacon",
                "command", "hashfiles",
                "config", "configBeacon", "logs", "help", "status", "clear", "exit",
            ]
            available_commands = [cmd for cmd in available_commands if cmd is not None]
            completer = WordCompleter(available_commands, ignore_case=True)

            while True:
                # Get user command with styled prompt
                try:
                    with patch_stdout():
                        # Use bottom toolbar to show stats
                        command = self.prompt_session.prompt(
                            ANSI(colorize("MultiHandler ❯ ", fg="bright_magenta", bold=True)),
                            completer=completer,
                            bottom_toolbar=self.ui_manager.get_bottom_toolbar,
                            refresh_interval=0.5
                        ).lower().strip()
                except EOFError:
                    c_error("\nUse 'exit' command to quit")
                    continue
                    
                if not command:
                    continue
                    
                logger.debug(f"Received command: {command}")
                
                # Status command - show activity panel
                if command == "status":
                    self.ui_manager.console.print()
                    self.ui_manager.print_activity_sidebar()
                    self.ui_manager.console.print()
                    continue
                
                log_connection_event("command", f"Executing: {command}")
                
                # Exit command - shutdown server
                if command == "exit":
                    c_error("Closing connections")
                    log_connection_event("info", "Server shutting down")
                    break

                # --------------------------------------------------------
                # Command Handler Functions
                # --------------------------------------------------------
                
                def handle_sessions():
                    """Route to session selection interface."""
                    logger.debug("Handling sessions command")
                    if len(sessions_list) == 0:
                        c_error("No sessions connected")
                    else:
                        self.multihandlercommands.sessionconnect()

                def handle_beacons():
                    """Route to beacon selection interface."""
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
                            logger.info(
                                f"Using beacon {beacon.uuid} at {beacon.address}"
                            )
                        except IndexError:
                            c_error("Index out of range")
                            logger.error("Index out of range for beacon selection")
                    else:
                        beacon = list(beacon_list.values())[0]
                        self.multihandlercommands.use_beacon(
                            beacon.uuid,
                            beacon.address
                        )

                # Command routing dictionary
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
                    "users": (
                        self.multiplayer.userMenu if self.isMultiplayer
                        else (lambda: c_error("Multiplayer mode is not enabled"))
                    ),
                    "logs": self.multihandlercommands.view_logs,
                    "clear": self.ui_manager.clear_screen,
                }

                # Execute command
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
        finally:
            # Stop the live display
            self.ui_manager.stop_display()
        return