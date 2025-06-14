from hashlib import sha512
import secrets 
import hmac    
import os
from ..global_objects import config, logger

class Authentication:
    # ... (__init__ method remains the same) ...
    def __init__(self) -> None:
        logger.debug("Authentication module initialized")
        key_dir = os.path.expanduser("~/.PrometheanProxy/Certificates")
        self.key_file_path = os.path.join(key_dir, "hmac.key")
        os.makedirs(key_dir, exist_ok=True)
        if os.path.isfile(self.key_file_path):
            with open(self.key_file_path, 'r', encoding='utf-8') as f: key_str = f.read().strip()
        else:
            key_str = secrets.token_hex(32) 
            with open(self.key_file_path, 'w', encoding='utf-8') as f: f.write(key_str)
            try:
                os.chmod(self.key_file_path, 0o600)
            except OSError as e:
                logger.error(f"Failed to set file permissions for HMAC key: {e}")
        self.shared_key = key_str.encode('utf-8')
        self.keylength = config['authentication']['keylength']
        self.key = ""  
        self.auth_key = "" 

    def get_authentication_string(self):
        """Generates the nonce."""
        logger.debug("Generating secure authentication challenge (nonce)")
        self.key = secrets.token_hex(self.keylength)
        logger.debug(f"Generated challenge (nonce): {self.key}")
        return self.key

    # CHANGED: The 'port' argument is no longer needed.
    def create_authentication_response(self):
        """Creates the correct auth key without the port."""
        logger.debug("Creating expected HMAC signature")

        # CHANGED: The message is now ONLY the nonce.
        message = self.key.encode('utf-8')
        logger.debug(f"Message to be signed: {message.decode()}")

        h = hmac.new(self.shared_key, message, sha512)
        self.auth_key = h.hexdigest()

        logger.debug(f"Expected HMAC signature: {self.auth_key}")
        return self.auth_key

    # CHANGED: The 'port' argument is no longer needed.
    def test_auth(self, returnedkey):
        """Tests the returned authentication key."""
        logger.debug("Testing client's authentication key")
        # Call the updated method without the port
        self.create_authentication_response()
        logger.debug(f"Returned key from client: {returnedkey}")
        logger.debug(f"Expected key by server:   {self.auth_key}")

        return hmac.compare_digest(self.auth_key, returnedkey)