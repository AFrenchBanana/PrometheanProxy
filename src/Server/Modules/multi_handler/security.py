# ============================================================================
# Multi Handler Security Module
# ============================================================================
# This module handles security-related functions including TLS certificate
# and HMAC key generation for secure client-server communication.
# ============================================================================

# Standard Library Imports
import os
import secrets

# Local Module Imports
from ..global_objects import config, logger
from ..utils.ui_manager import RichPrint


class SecurityMixin:
    """
    Mixin class providing security configuration methods.

    Provides methods for creating and managing TLS certificates and HMAC
    authentication keys used for secure communication with clients.
    """

    def create_hmac(self) -> None:
        """
        Create or verify HMAC authentication key.

        Checks if an HMAC key exists in the configured location. If not found,
        generates a new 32-byte (64 hex character) key for client authentication.
        The key file is created with restricted permissions (0o600) for security.
        """
        logger.info("Checking for HMAC key")
        cert_dir = os.path.expanduser(config["server"]["TLSCertificateDir"])
        hmac_key_path = os.path.join(cert_dir, "hmac.key")
        logger.debug(f"HMAC key path: {hmac_key_path}")

        if not os.path.isfile(hmac_key_path):
            logger.info("HMAC key not found, creating new one")
            if not os.path.isdir(cert_dir):
                logger.debug(f"Creating directory for HMAC key: {cert_dir}")
                os.makedirs(cert_dir, exist_ok=True)

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
                return

            logger.info("HMAC key created successfully")
            RichPrint.r_print("HMAC key created: " + f"{hmac_key_path}", style="green")
        else:
            logger.debug("HMAC key already exists")

    def create_certificate(self) -> None:
        """
        Create or verify TLS certificates for secure communication.

        Checks if TLS certificates exist in the configured location. If not found,
        generates new self-signed TLS certificates using OpenSSL for secure
        client-server communication.
        """
        logger.info("Checking for TLS certificates")
        cert_dir = os.path.expanduser(config["server"]["TLSCertificateDir"])
        tls_key = os.path.expanduser(config["server"]["TLSkey"])
        tls_cert = os.path.expanduser(config["server"]["TLSCertificate"])

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
                "openssl req -x509 -newkey rsa:2048 -nodes -keyout "
                + f"{key_path} -days 365 -out {cert_path} -subj "
                + "'/CN=localhost'"
            )
            logger.info("TLS certificates created successfully")
            RichPrint.r_print(
                "TLS certificates created: "
                + f"{cert_dir}{tls_key} and {cert_dir}{tls_cert}",
                style="green",
            )
        else:
            logger.debug("TLS certificates already exist")
