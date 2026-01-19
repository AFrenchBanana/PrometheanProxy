# ============================================================================
# Multi Handler Socket Server Module
# ============================================================================
# This module handles SSL socket server initialization and connection acceptance.
# ============================================================================

# Standard Library Imports
import json
import os
import socket
import ssl
import sys
import threading
from datetime import datetime

from ServerDatabase.database import DatabaseClass

# Local Imports
from ..global_objects import config, logger
from ..session.session import add_connection_list
from ..session.transfer import receive_data, send_data
from ..utils.ui_manager import RichPrint

# Global socket references
SSL_Socket = None
socket_clear = None


class SocketServerMixin:
    """
    Mixin class providing SSL socket server functionality.

    This mixin provides methods for initializing and starting the SSL socket
    server, as well as accepting and authenticating incoming connections.
    """

    def startsocket(self) -> None:
        """
        Initialize and start the SSL socket server.

        Creates an SSL context, loads certificates, binds to the configured
        address and port, and begins listening for incoming connections.
        Starts a daemon thread to accept new connections.
        """
        global SSL_Socket, socket_clear

        try:
            logger.info("Starting socket server")

            # Get listening configuration from config
            self.address = (config["server"]["listenaddress"], config["server"]["port"])
            logger.debug(f"Socket address: {self.address}")

            # Create SSL context for secure communication
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            logger.debug("Creating SSL context")

            # Load TLS certificates
            cert_dir = os.path.expanduser(config["server"]["TLSCertificateDir"])

            le_cert_path = os.path.join(cert_dir, "fullchain.pem")
            le_key_path = os.path.join(cert_dir, "privkey.pem")

            if os.path.exists(le_cert_path) and os.path.exists(le_key_path):
                logger.info("Found Let's Encrypt certificates, using them.")
                tls_cert = "fullchain.pem"
                tls_key = "privkey.pem"
            else:
                logger.info(
                    "Let's Encrypt certificates not found, using self-signed certificates."
                )
                tls_key = config["server"]["TLSkey"]
                tls_cert = config["server"]["TLSCertificate"]

            logger.debug(
                f"Certificate directory: {cert_dir}, Key: {tls_key}, Cert: {tls_cert}"
            )
            context.load_cert_chain(
                certfile=os.path.join(cert_dir, tls_cert),
                keyfile=os.path.join(cert_dir, tls_key),
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
            RichPrint.r_print("TLS certificate or key file not found.", style="red")
            sys.exit(1)
        except ssl.SSLError as e:
            logger.critical(f"SSL error: {e}")
            RichPrint.r_print("SSL error: " + str(e), style="red")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            RichPrint.r_print("Unexpected error: " + str(e), style="red")
            sys.exit(1)

        # Bind socket to address and start listening
        try:
            SSL_Socket.bind(self.address)
            logger.info(f"Socket bound to {self.address[0]}:{self.address[1]}")
        except OSError:
            logger.error(f"Socket {self.address[0]}:{self.address[1]} already in use")
            RichPrint.r_print(
                f"{self.address[0]}:{self.address[1]} already in use", style="red"
            )
            logger.critical("Exiting due to socket error")
            sys.exit(1)

        SSL_Socket.listen()
        logger.info(f"Socket listening on {self.address[0]}:{self.address[1]}")

        # Start connection accept thread
        listenerthread = threading.Thread(target=self.accept_connection, args=())
        logger.debug("Starting listener thread for accepting connections")
        listenerthread.daemon = True
        listenerthread.start()
        return

    def accept_connection(self) -> None:
        """
        Accept and authenticate incoming client connections.

        Continuously listens for new connections, performs authentication,
        and adds authenticated clients to the appropriate session list.
        Runs in a daemon thread started by startsocket().
        """
        global SSL_Socket

        # Use shared database instance to avoid multiple initializations
        from Modules import global_objects

        threadDB = global_objects.get_database("command_database")
        logger.info("Accepting connections on socket")

        while True:
            conn, r_address = SSL_Socket.accept()
            logger.info(f"Connection accepted from {r_address[0]}:{r_address[1]}")

            # Send authentication challenge
            send_data(conn, self.Authentication.get_authentication_string())
            logger.debug("Sent authentication string to client")

            # Verify authentication response
            if self.Authentication.test_auth(receive_data(conn)):
                logger.info(
                    f"Authentication successful for {r_address[0]}:{r_address[1]}"
                )

                # Receive client information
                data = receive_data(conn)
                logger.debug(f"Received data from client: {data}")
                try:
                    data_json = json.loads(data)
                    hostname = data_json.get("Hostname")
                    os_info = data_json.get("OS")
                    client_id = data_json.get("ID")
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Failed to decode JSON data: {e}")
                    os_info = None
                    client_id = None

                logger.debug(f"Received hostname from client: {hostname}")

                # Send packet sniffer configuration
                send_data(conn, str(config["packetsniffer"]["active"]))
                logger.debug(f"OS: {os_info}, ID: {client_id}")
                if config["packetsniffer"]["active"]:
                    send_data(conn, str(config["packetsniffer"]["port"]))
                    logger.debug("Sent packet sniffer port to client")

                # Check if this is a beacon switching to session mode
                from ..beacon.beacon import remove_beacon_list
                from ..global_objects import beacon_list

                if client_id and client_id in beacon_list:
                    logger.info(f"Beacon {client_id} switching to session mode")
                    # Update database to track mode switch
                    import time

                    threadDB.update_entry(
                        "connections",
                        "connection_type=?, last_mode_switch=?, session_address=?",
                        ("session", time.time(), f"{r_address[0]}:{r_address[1]}"),
                        "uuid=?",
                        (client_id,),
                    )
                    # Remove from beacon list
                    remove_beacon_list(client_id)
                    logger.info(
                        f"Removed {client_id} from beacon list, now in session mode"
                    )

                # Add connection to sessions list
                add_connection_list(
                    conn, r_address, hostname, os_info, client_id, "session", [], config
                )
                logger.info(
                    f"Added connection to sessions list: {hostname} ({os_info})"
                )

                # Log connection to database
                threadDB.insert_entry(
                    "Addresses",
                    [
                        client_id,
                        r_address[0],
                        r_address[1],
                        hostname,
                        os_info,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                )
            else:
                conn.close()
