from global_objects import logger
import os
import hashlib
import bcrypt
from ServerDatabase.database import DatabaseClass

class User:
    """
    This class represents a user in the multiplayer system.
    It contains user-related information and methods for user management.
    """
    def __init__(self, username, password):
        self.username = username
        self.password = self.hashPassword_bcrypt(password)
        self.passwordSalt = None
        self.admin = False
        logger.info(f"User {self.username} created")
    
    def __str__(self):
        return f"User(username={self.username})"
    
    def update_password(self, new_password):
        self.password = self.hashPassword_bcrypt(new_password)

    def hashPassword_bcrypt(self, password):
        """
        Hash the user's password using bcrypt.
        """
        salt, self.passwordSalt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt)

    def verifyPassword_bcrypt(self, password, hashed):
        """
        Verify a password against the stored bcrypt hash.
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    def authenticate(self, password) -> bool:
        """
        Authenticate the user with the provided password.
        Returns True if authentication is successful, False otherwise.
        """
        if self.verifyPassword_bcrypt(password, self.password):
            self.is_authenticated = True
            logger.info(f"User {self.username} authenticated successfully")
            return True, 
        else:
            logger.warning(f"Authentication failed for user {self.username}")
            return False
    

class MP_Users:
    """
    This class manages multiplayer user sessions and interactions.
    It handles user authentication, session management, and user data storage.
    """
    def __init__(self, config):
        self.config = config
        self.database = DatabaseClass(config['server']['database'])
        logger.info("MP_Users instance created with database connection")
        self.load_users()

    def load_users(self):
        logger.info("Loading users from the database")


    def authenticate_user(self, username, password):
        """
        Authenticate a user with the provided username and password.
        Returns True if authentication is successful, False otherwise.
        """
        # Placeholder for actual authentication logic
        logger.debug(f"Authenticating user: {username}")
        return True  # Simulate successful authentication

    def add_user(self):
        username = input("Enter username: ")
        password = input("Enter password: ")
        new_user = User(username, password)
        logger.info(f"Adding user: {username}")
        self.database.insert_entry('users', (new_user.username, new_user.password, new_user.passwordSalt, new_user.admin))  
    def remove_user(self, username):
        """
        Remove a user from the multiplayer system.
        """
        logger.info(f"Removing user: {username}")
        # Placeholder for actual user removal logic