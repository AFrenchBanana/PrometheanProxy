from ..global_objects import logger
from ..utils.console import cprint, error as c_error
import colorama
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
        self.auth_token = None
        self.auth_token_expiry = None
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
        salt = bcrypt.gensalt()
        self.passwordSalt = salt
        return bcrypt.hashpw(password.encode('utf-8'), salt)

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
        # self.database = DatabaseClass(config['server']['database'])
        logger.info("MP_Users instance created with database connection")
        self.users = {}
        self.load_users()
        self.current_user = "admin"  # temp
        self.add_user("test", "test")  # Add a test user for initial testing
        cprint(f"You are logged in as {self.current_user}", fg="green")

    def currentUser(self) -> str:
        return self.current_user

    def load_users(self):
        # temp til we add storage
        self.add_user("Admin", "admin")
        self.current_user = "Admin"

    def authenticate_user(self, username, password) -> bool:
        """
        Authenticate a user with the provided username and password.
        Returns True if authentication is successful, False otherwise.
        """
        user = self.users.get(username)
        if not user:
            logger.warning(f"User {username} not found")
            return False

        if user.authenticate(password):
            self.current_user = username
            logger.info(f"User {username} authenticated successfully")
            return True
        else:
            logger.warning(f"Authentication failed for user {username}")
            return False


    def add_user_input(self):
        username = input("Enter username: ")
        password = input("Enter password: ")
        if username in self.users:
            logger.warning(f"User {username} already exists")
            print(f"User {username} already exists.")
            return
        self.add_user(username, password)
    
    def add_user(self, username: str, password: str):
        """
        Add a new user to the multiplayer system.
        """
        username = username.strip().lower()
        if username in self.users:
            logger.warning(f"User {username} already exists")
            print(f"User {username} already exists.")
            return
        
        user = User(username, password)
        self.users[username] = user
        logger.info(f"User {username} added successfully")
        print(f"User {username} added successfully")

    def list_users(self) -> str:
        """
        List all users in the multiplayer system.
        """
        if not self.users:
            logger.info("No users found")
            return "No users found"
        
        print("Current Users:")
        userList = ""
        for username, user in self.users.items():
            if self.current_user == username:
                userList += f"Username: {username} (Current User)\n"
            if any(c.user == username for c in self.currentConnections):
                userList += f"Username: {username}: (Remotley logged in)\n"
            else:
                userList += f"Username: {username}\n"
            logger.info(f"User listed: {username}")
        return userList


    def remove_user(self, username):
        """
        Remove a user from the multiplayer system.
        """
        logger.info(f"Removing user: {username}")
        # Placeholder for actual user removal logic

    def switch_user_input(self):
        username = input("Enter username to switch to: ")
        import getpass
        password = getpass.getpass("Enter password: ")
        self.switchUser(username, password)
    
    def switchUser(self, username: str, password: str) -> None:
        """
        Switch the current user to the specified username.
        """
        if username in self.users:
            if self.authenticate_user(username, password):
                logger.info(f"Switching to user: {username}")
                self.current_user = username
                logger.info(f"Switched to user: {username}")
                cprint(f"Switched to user: {username}", fg="green")
            else:
                logger.warning(f"Authentication failed for user {username}")
                c_error(f"Authentication failed for user {username}")
        else:
            logger.warning(f"User {username} does not exist")
            c_error(f"User {username} does not exist")
        