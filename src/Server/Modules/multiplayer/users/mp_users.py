import uuid
from ...global_objects import logger
from ...utils.console import cprint, error as c_error
import colorama
import bcrypt
from ServerDatabase.database import DatabaseClass
from typing import Optional
from Modules.utils.console import cprint, warn, error as c_error

class User:
    """
    This class represents a user in the multiplayer system.
    It contains user-related information and methods for user management.
    Attributes:
        username (str): The username of the user
        password (bytes): The hashed password of the user
        passwordSalt (bytes): The salt used for hashing the password
        auth_token (str): The authentication token for the user session
        auth_token_expiry (datetime): The expiry time of the authentication token
        admin (bool): Flag indicating if the user has admin privileges
    Methods:
        __str__(): Returns a string representation of the User object
        update_password(new_password): Updates the user's password
        hashPassword_bcrypt(password): Hashes a password using bcrypt
        verifyPassword_bcrypt(password, hashed): Verifies a password against a hashed password
        authenticate(password): Authenticates the user with the provided password   
    """
    def __init__(self, username: str, password: str, is_admin: bool = False, database: Optional[DatabaseClass] = None):
        """
        Initialize a User object with the given username and password.
        Args:
            username (str): The username of the user
            password (str): The password of the user
            database (DatabaseClass, optional): The database connection for user data storage
        Returns:
            None      
        """
        self.userID = str(uuid.uuid4())
        self.username = username
        self.password = self.hashPassword_bcrypt(password)
        self.passwordSalt = None
        self.auth_token = None
        self.auth_token_expiry = None
        self.admin = is_admin
        if database != None:
            self.database = database
            self._add_user_to_db()
        logger.info(f"User {self.username} created")

    @classmethod
    def from_db_row(cls, row, database):
        """
        Create a User object from a database row.
        Args:
            row (tuple): The database row data
            database (DatabaseClass): The database connection
        Returns:
            User: The created User object
        """
        user = cls.__new__(cls)
        user.userID = row[0] # uuid string
        user.username = row[1]
        user.password = row[2].encode('utf-8') if row[2] else b''
        user.passwordSalt = row[3].encode('utf-8') if row[3] else None
        user.admin = bool(row[4])
        user.database = database
        user.auth_token = None
        user.auth_token_expiry = None
        return user
       
    
    def __str__(self):
        """
        String representation of the User object.
        """
        return f"User(username={self.username})"
    
    def _add_user_to_db(self):
        """
        Add the user to the database.
        Args:
            None
        Returns:
            None
        """
        if not hasattr(self, 'database'):
            logger.error("Database connection not provided for user")
            return
        self.database.insert_entry("Users", (
            str(self.userID),
            self.username,
            self.password.decode('utf-8'),
            self.passwordSalt.decode('utf-8') if self.passwordSalt else None,
            self.admin
        ))
        logger.info(f"User {self.username} added to database")
        return

    
    def update_password(self, new_password):
        """
        Update the user's password.
        Args:
            new_password (str): The new password to set
        Returns:
            None
        """
        self.password = self.hashPassword_bcrypt(new_password)

    def hashPassword_bcrypt(self, password) -> bytes:
        """
        Hash a password using bcrypt.
        Args:
            password (str): The password to hash
        Returns:
            bytes: The hashed password
        """
        salt = bcrypt.gensalt()
        self.passwordSalt = salt
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    def verifyPassword_bcrypt(self, password, hashed) -> bool:
        """
        Verify a password against a hashed password using bcrypt.
        Args:
            password (str): The password to verify
            hashed (bytes): The hashed password to compare against
        Returns:
            bool: True if the password matches the hash, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    def authenticate(self, password) -> bool:
        """
        Authenticate the user with the provided password.
        Args:
            password (str): The password to authenticate
        Returns:
            bool: True if authentication is successful, False otherwise
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
        self.users = {}
        self.config = config
        self.database = DatabaseClass(config, "user_database")
        self.load_users()
        self._create_admin()
        self.add_user("test", "test") # Default test user for testing purposes
        self._load_current_user()

        username = self.users[self.current_user].username if self.current_user in self.users else "Unknown"
        cprint(f"You are logged in as {username}", fg="green")

    def _load_current_user(self):
        """
        Load the current user from the terminal_user table.
        Args:
            None
        Returns:
            None
        """
        terminal_users = self.database.fetch_all('terminal_user')
        found = False
        if terminal_users:
            userID = terminal_users[0][1] 
            if userID in self.users:
                self.current_user = userID
                logger.info(f"Current user loaded: {self.current_user}")
                found = True
            else:
                logger.warning(f"User {userID} not found, defaulting to admin")
        
        if not found:
            admin = next((u for u in self.users.values() if u.username == 'admin'), None)
            if admin:
                self.current_user = admin.userID
                logger.info("Defaulting to admin")
            else:
                logger.error("Admin user not found during default login")
                self._create_admin()
                self.current_user = next((u.userID for u in self.users.values() if u.username == 'admin'), None)
                logger.info("Admin user created and set as current user")

    def _create_admin(self):
        """
        Create a default admin user if none exist.
        Args:
            None
        Returns:
            None
        """
        if not any(user.admin for user in self.users.values()):
            admin_user = User("admin", "admin", is_admin=True, database=self.database)
            self.users[admin_user.userID] = admin_user
            logger.info("Default admin user created")
            cprint("Default admin user created with username 'admin' and password 'admin'", fg="yellow")

    @property
    def currentUserName(self) -> str:
        return self.users[self.current_user].username if self.current_user in self.users else "Unknown"

    def load_users(self) -> None:
        """
        Load users from the database into the MP_Users instance.
        Args:
            None
        Returns:
            None
        """
        users_data = self.database.fetch_all('Users')
        for row in users_data:
            try:
                user = User.from_db_row(row, self.database)
                self.users[user.userID] = user
                logger.debug(f"Loaded user {user.username} from database")
            except Exception as e:
                logger.error(f"Failed to load user from row {row}: {e}")
        

    def authenticate_user(self, username, password) -> bool:
        """
        Authenticate a user with the provided username and password.
        Args:
            username (str): The username of the user to authenticate
            password (str): The password of the user to authenticate
        Returns:
            bool: True if authentication is successful, False otherwise
        """
        user = next((u for u in self.users.values() if u.username == username), None)
        if not user:
            logger.warning(f"User {username} not found")
            return False

        if user.authenticate(password):
            self.current_user = user.userID
            logger.info(f"User {username} authenticated successfully")
            return True
        else:
            logger.warning(f"Authentication failed for user {username}")
            return False


    def add_user_input(self):
        """
        Prompt for username and password to add a new user.
        Args:
            None
        Returns:
            None
        """
        if self.users[self.current_user].admin is not True:
            logger.warning(f"Only admin users can create new users")
            warn("Only admin users can create new users.")
            return
        username = input("Enter username: ")
        password = input("Enter password: ")
        is_admin = input("Is this user an admin? (y/n): ").strip().lower() == 'y'
        if any(u.username == username for u in self.users.values()):
            logger.warning(f"User {username} already exists")
            print(f"User {username} already exists.")
            return

        self.add_user(username, password, is_admin=is_admin)
    
    def add_user(self, username: str, password: str, is_admin: Optional[bool] = False) -> None:
        """
        Add a new user to the multiplayer system.
        Args:
            username (str): The username of the new user
            password (str): The password of the new user
            is_admin (bool, optional): Flag indicating if the user has admin privileges
        Returns:
            None
        """
        username = username.strip().lower()
        if any(u.username == username for u in self.users.values()):
            logger.warning(f"User {username} already exists")
            print(f"User {username} already exists.")
            return
        if is_admin is True:
            if self.users[self.current_user].admin is not True:
                logger.warning(f"Only admin users can create new admin users")
                warn("Only admin users can create new admin users.")
                return
        user = User(username, password, is_admin=is_admin, database=self.database)
        self.users[user.userID] = user
        logger.info(f"User {username} added successfully")
        print(f"User {username} added successfully")

    def list_users(self) -> str:
        """
        List all users in the multiplayer system.
        Args:
            None
        Returns:
            str: A formatted string listing all users
        """
        if not self.users:
            logger.info("No users found")
            return "No users found"
        
        print("Current Users:")
        userList = ""
        for userID, user in self.users.items():
            username = user.username
            if self.current_user == userID:
                userList += f"Username: {username} (Current User)\n"
            elif self.current_user != userID and user.auth_token is not None:
                userList += f"Username: {username}: (Remotley logged in)\n"
            else:
                userList += f"Username: {username}\n"
            logger.info(f"User listed: {username}")
        return userList


    def remove_user(self, username):
        """
        Remove a user from the multiplayer system.
        Args:
            username (str): The username of the user to remove
        Returns:
            None
        """
        logger.info(f"Removing user: {username}")
        # Placeholder for actual user removal logic

    def switch_user_input(self):
        """
        Prompt for username and password to switch the current user.
        Args:
            None
        Returns:
            None
        """
        username = input("Enter username to switch to: ")
        import getpass
        password = getpass.getpass("Enter password: ")
        self.switchUser(username, password)
    
    def switchUser(self, username: str, password: str) -> None:
        """
        Switch the current user to the specified username after authentication.
        Args:
            username (str): The username to switch to
            password (str): The password for authentication
        Returns:
            None
        """
        if any(u.username == username for u in self.users.values()):
            if self.authenticate_user(username, password):
                logger.info(f"Switching to user: {username}")
                # self.current_user is updated in authenticate_user
                logger.info(f"Switched to user: {username}")
                cprint(f"Switched to user: {username}", fg="green")
            else:
                logger.warning(f"Authentication failed for user {username}")
                c_error(f"Authentication failed for user {username}")
        else:
            logger.warning(f"User {username} does not exist")
            c_error(f"User {username} does not exist")
        