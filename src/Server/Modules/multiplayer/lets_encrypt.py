import http.server
import logging
import os
import socketserver
import ssl
import threading
import time

from acme import challenges, client, messages
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Configure logging
logger = logging.getLogger(__name__)


class ChallengeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/.well-known/acme-challenge/"):
            token = os.path.basename(self.path)
            challenge_dir = os.path.join(os.getcwd(), ".well-known/acme-challenge")
            challenge_file = os.path.join(challenge_dir, token)
            if os.path.exists(challenge_file):
                self.send_response(200)
                self.end_headers()
                with open(challenge_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


class LetsEncrypt:
    def __init__(self, email, domains, cert_dir):
        self.email = email
        self.domains = domains
        self.cert_dir = cert_dir
        self.account_key = None
        self.client = None
        self.http_server = None

    def _generate_private_key(self, key_size=2048):
        return rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )

    def _get_or_create_account_key(self):
        key_path = os.path.join(self.cert_dir, "account.key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
        else:
            key = self._generate_private_key()
            with open(key_path, "wb") as f:
                f.write(
                    key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
            return key

    def _create_client(self):
        self.account_key = self._get_or_create_account_key()
        self.client = client.ClientV2(
            "https://acme-v02.api.letsencrypt.org/directory", self.account_key
        )
        # Register the account if it doesn't exist
        try:
            self.client.new_account(
                messages.NewRegistration.from_data(
                    email=self.email, terms_of_service_agreed=True
                )
            )
        except messages.Error as e:
            if "already exists" not in str(e):
                raise

    def _start_http_server(self):
        challenge_dir = os.path.join(os.getcwd(), ".well-known/acme-challenge")
        os.makedirs(challenge_dir, exist_ok=True)
        self.http_server = socketserver.TCPServer(("", 80), ChallengeHandler)
        server_thread = threading.Thread(target=self.http_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def _stop_http_server(self):
        if self.http_server:
            self.http_server.shutdown()

    def _authorize_domain(self, domain):
        logger.info(f"Authorizing domain: {domain}")
        order = self.client.new_order([domain])
        challenge = [
            c
            for c in order.authorizations[0].challenges
            if isinstance(c.chall, challenges.HTTP01)
        ][0]
        token = challenge.chall.token
        key_authorization = challenge.key_authorization(self.account_key)

        challenge_dir = os.path.join(os.getcwd(), ".well-known/acme-challenge")
        with open(os.path.join(challenge_dir, token), "w") as f:
            f.write(key_authorization)

        self.client.answer_challenge(challenge, key_authorization)

        # Wait for authorization to complete
        # In a real implementation, you would poll the authorization status
        time.sleep(5)
        logger.info(f"Domain {domain} authorized")
        return order

    def _finalize_order(self, order):
        logger.info("Finalizing order")
        csr_key = self._generate_private_key()
        csr = self.client.new_csr(self.domains, csr_key)
        order = self.client.poll_and_finalize(order, csr)

        cert_path = os.path.join(self.cert_dir, "cert.pem")
        chain_path = os.path.join(self.cert_dir, "chain.pem")
        fullchain_path = os.path.join(self.cert_dir, "fullchain.pem")
        privkey_path = os.path.join(self.cert_dir, "privkey.pem")

        with open(fullchain_path, "wb") as f:
            f.write(order.fullchain_pem.encode("utf-8"))

        with open(privkey_path, "wb") as f:
            f.write(
                csr_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        logger.info("Certificate issued and saved")

    def get_certificate(self):
        self._create_client()
        self._start_http_server()
        try:
            for domain in self.domains:
                order = self._authorize_domain(domain)
                self._finalize_order(order)
        finally:
            self._stop_http_server()

    def renew_certificate(self):
        # In a real implementation, you would check the certificate's expiration date
        # and renew it if necessary.
        self.get_certificate()
