"""
Authentication module handles the initial
authentication processes off the server.
has the ability to produce random strings,
format it for the authentication and test
the returned string
"""

from hashlib import sha512
import string
import random
from .global_objects import config, logger


class Authentication:
    """
    class that handles authentication requests when a
    client connects, helps prevent
    rogue clients from connectiong
    """

    def __init__(self) -> None:
        logger.debug("Authentication module initialized")
        self.keylength = config['authentication']['keylength']
        self.key = ""
        self.auth_key = ""

    def get_authentication_string(self):
        """
        creates a random string of ascii characters
        based on the length specified
        from the key length
        """
        logger.debug("Generating authentication key")
        self.key = "".join(random.choice(string.ascii_letters)
                           for i in range(self.keylength))
        logger.debug(f"Generated key: {self.key}")
        return self.key

    def create_authentication_response(self, port):
        """creates the correct authentication key"""
        logger.debug("Creating authentication response")
        auth_key = (f"{self.key}{port}")[
            ::-1]  # adds the port to the key and reverses it
        logger.debug(f"Authentication key before hashing: {auth_key}")
        self.auth_key = (sha512(auth_key.encode()).hexdigest()
                         )  # hashes the key as sha512
        logger.debug(f"Authentication key after hashing: {self.auth_key}")
        return self.auth_key

    def test_auth(self, returnedkey, port):
        """tests the returned authentication key against the correct key """
        logger.debug("Testing authentication key")
        self.create_authentication_response(port)
        logger.debug(f"Returned key: {returnedkey}")
        return self.auth_key == returnedkey
