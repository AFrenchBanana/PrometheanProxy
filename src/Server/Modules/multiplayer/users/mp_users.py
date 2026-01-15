import getpass
import uuid
from typing import Optional

import bcrypt
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from ServerDatabase.database import DatabaseClass

from ...global_objects import logger
from ...utils.ui_manager import get_ui_manager


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

    def __init__(
        self,
        username: str,
        password: str,
        is_admin: bool = False,
        database: Optional[DatabaseClass] = None,
    ):
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
        if database is not None:
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
        user.userID = row[0]  # uuid string
        user.username = row[1]
        user.password = row[2].encode("utf-8") if row[2] else b""
        user.passwordSalt = row[3].encode("utf-8") if row[3] else None
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
        if not hasattr(self, "database"):
            logger.error("Database connection not provided for user")
            return
        self.database.insert_entry(
            "Users",
            (
                str(self.userID),
                self.username,
                self.password.decode("utf-8"),
                self.passwordSalt.decode("utf-8") if self.passwordSalt else None,
                self.admin,
            ),
        )
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
        return bcrypt.hashpw(password.encode("utf-8"), salt)

    def verifyPassword_bcrypt(self, password, hashed) -> bool:
        """
        Verify a password against a hashed password using bcrypt.
        Args:
            password (str): The password to verify
            hashed (bytes): The hashed password to compare against
        Returns:
            bool: True if the password matches the hash, False otherwise
        """
        return bcrypt.checkpw(password.encode("utf-8"), hashed)

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
            return True
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
        # Use shared database instance to avoid multiple initializations
        from Modules import global_objects

        self.database = global_objects.get_database("user_database")
        self.ui = get_ui_manager()
        self.prompt_session = PromptSession()
        self.load_users()
        self._create_admin()
        self.add_user("test", "test")  # Default test user for testing purposes
        self._load_current_user()

        username = (
            self.users[self.current_user].username
            if self.current_user in self.users
            else "Unknown"
        )
        self.ui.print_success(f"You are logged in as [bright_cyan]{username}[/]")

    def _load_current_user(self):
        """
        Load the current user from the terminal_user table.
        Args:
            None
        Returns:
            None
        """
        terminal_users = self.database.fetch_all("terminal_user")
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
            admin = next(
                (u for u in self.users.values() if u.username == "admin"), None
            )
            if admin:
                self.current_user = admin.userID
                logger.info("Defaulting to admin")
            else:
                logger.error("Admin user not found during default login")
                self._create_admin()
                self.current_user = next(
                    (u.userID for u in self.users.values() if u.username == "admin"),
                    None,
                )
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
            self.ui.print_warning(
                "Default admin user created with username [bright_cyan]'admin'[/] and password [bright_cyan]'admin'[/]"
            )

    @property
    def currentUserName(self) -> str:
        return (
            self.users[self.current_user].username
            if self.current_user in self.users
            else "Unknown"
        )

    def load_users(self) -> None:
        """
        Load users from the database into the MP_Users instance.
        Args:
            None
        Returns:
            None
        """
        users_data = self.database.fetch_all("Users")
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
        Uses styled prompts and modern UI.
        Args:
            None
        Returns:
            None
        """
        if self.users[self.current_user].admin is not True:
            logger.warning("Only admin users can create new users")
            self.ui.print_warning("Only admin users can create new users.")
            return

        self.ui.print_info("Creating a new user...")

        try:
            username = self.prompt_session.prompt(
                "[+] Enter username: ",
            ).strip()

            if not username:
                self.ui.print_error("Username cannot be empty.")
                return

            password = getpass.getpass("[+] Enter password: ")

            if not password:
                self.ui.print_error("Password cannot be empty.")
                return

            # Admin role prompt with completer
            role_completer = WordCompleter(["yes", "no", "y", "n"], ignore_case=True)
            is_admin_input = (
                self.prompt_session.prompt(
                    "[+] Is this user an admin? (y/n): ",
                    completer=role_completer,
                )
                .strip()
                .lower()
            )
            is_admin = is_admin_input in ("y", "yes")

            if any(u.username == username for u in self.users.values()):
                logger.warning(f"User {username} already exists")
                self.ui.print_error(f"User [bright_cyan]{username}[/] already exists.")
                return

            self.add_user(username, password, is_admin=is_admin)

        except KeyboardInterrupt:
            self.ui.print_warning("User creation cancelled.")
            return
        except EOFError:
            self.ui.print_warning("User creation cancelled.")
            return

    def add_user(self, username: str, password: str, is_admin: bool = False) -> None:
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
            self.ui.print_error(f"User [bright_cyan]{username}[/] already exists.")
            return
        if is_admin is True:
            if self.users[self.current_user].admin is not True:
                logger.warning("Only admin users can create new admin users")
                self.ui.print_warning("Only admin users can create new admin users.")
                return
        user = User(username, password, is_admin=bool(is_admin), database=self.database)
        self.users[user.userID] = user
        logger.info(f"User {username} added successfully")
        role_str = "[bright_red]admin[/]" if is_admin else "[white]user[/]"
        self.ui.print_success(
            f"User [bright_cyan]{username}[/] added successfully as {role_str}"
        )

    def list_users(self) -> None:
        """
        List all users in the multiplayer system using a modern styled table.
        Args:
            None
        Returns:
            None
        """
        if not self.users:
            logger.info("No users found")
            self.ui.print_info("No users found")
            return

        # Create and display the users table
        table = self.ui.create_users_table(self.users, self.current_user)
        self.ui.console.print(table)
        self.ui.print_info(f"Total users: [bright_cyan]{len(self.users)}[/]")

    def remove_user(self, username: str) -> None:
        """
        Remove a user from the multiplayer system.
        Args:
            username (str): The username of the user to remove
        Returns:
            None
        """
        if self.users[self.current_user].admin is not True:
            logger.warning("Only admin users can remove users")
            self.ui.print_warning("Only admin users can remove users.")
            return

        user = next((u for u in self.users.values() if u.username == username), None)
        if not user:
            logger.warning(f"User {username} not found")
            self.ui.print_error(f"User [bright_cyan]{username}[/] not found.")
            return

        if user.userID == self.current_user:
            self.ui.print_error("Cannot remove the currently logged in user.")
            return

        if user.admin:
            admin_count = sum(1 for u in self.users.values() if u.admin)
            if admin_count <= 1:
                self.ui.print_error("Cannot remove the last admin user.")
                return

        # Remove from database
        try:
            self.database.delete_entry("Users", "userID", user.userID)
        except Exception as e:
            logger.error(f"Failed to remove user from database: {e}")

        del self.users[user.userID]
        logger.info(f"User {username} removed")
        self.ui.print_success(f"User [bright_cyan]{username}[/] removed successfully.")

    def remove_user_input(self) -> None:
        """
        Prompt for username to remove a user.
        Args:
            None
        Returns:
            None
        """
        if self.users[self.current_user].admin is not True:
            logger.warning("Only admin users can remove users")
            self.ui.print_warning("Only admin users can remove users.")
            return

        self.ui.print_info("Remove a user...")

        # Show current users
        self.list_users()

        try:
            # Create completer with existing usernames
            usernames = [u.username for u in self.users.values()]
            user_completer = WordCompleter(usernames, ignore_case=True)

            username = self.prompt_session.prompt(
                "[+] Enter username to remove: ",
                completer=user_completer,
            ).strip()

            if not username:
                self.ui.print_warning("Operation cancelled.")
                return

            # Confirm removal
            confirm = (
                self.prompt_session.prompt(
                    f"[!] Are you sure you want to remove '{username}'? (y/n): ",
                )
                .strip()
                .lower()
            )

            if confirm in ("y", "yes"):
                self.remove_user(username)
            else:
                self.ui.print_info("User removal cancelled.")

        except KeyboardInterrupt:
            self.ui.print_warning("Operation cancelled.")
        except EOFError:
            self.ui.print_warning("Operation cancelled.")

    def switch_user_input(self):
        """
        Prompt for username and password to switch the current user.
        Uses styled prompts and modern UI.
        Args:
            None
        Returns:
            None
        """
        self.ui.print_info("Switch user...")

        try:
            # Create completer with existing usernames
            usernames = [u.username for u in self.users.values()]
            user_completer = WordCompleter(usernames, ignore_case=True)

            username = self.prompt_session.prompt(
                "[+] Enter username to switch to: ",
                completer=user_completer,
            ).strip()

            if not username:
                self.ui.print_warning("Switch cancelled.")
                return

            password = getpass.getpass("[+] Enter password: ")
            self.switchUser(username, password)

        except KeyboardInterrupt:
            self.ui.print_warning("Switch cancelled.")
        except EOFError:
            self.ui.print_warning("Switch cancelled.")

    def switchUser(self, username: str, password: str) -> None:
        """
        Switch the current user to the specified username after authentication.
        Args:
            username (str): The username to switch to
            password (str): The password for authentication
        Returns:
            None
        """
        user = next((u for u in self.users.values() if u.username == username), None)
        if user:
            if self.authenticate_user(username, password):
                logger.info(f"Switching to user: {username}")
                logger.info(f"Switched to user: {username}")
                self.ui.print_success(f"Switched to user: [bright_cyan]{username}[/]")
            else:
                logger.warning(f"Authentication failed for user {username}")
                self.ui.print_error(
                    f"Authentication failed for user [bright_cyan]{username}[/]"
                )
        else:
            logger.warning(f"User {username} does not exist")
            self.ui.print_error(f"User [bright_cyan]{username}[/] does not exist")

    def change_password_input(self) -> None:
        """
        Prompt to change the current user's password.
        Args:
            None
        Returns:
            None
        """
        self.ui.print_info("Change password...")

        try:
            current_password = getpass.getpass("[+] Enter current password: ")

            # Verify current password
            current_user = self.users.get(self.current_user)
            if not current_user or not current_user.authenticate(current_password):
                self.ui.print_error("Current password is incorrect.")
                return

            new_password = getpass.getpass("[+] Enter new password: ")
            confirm_password = getpass.getpass("[+] Confirm new password: ")

            if new_password != confirm_password:
                self.ui.print_error("Passwords do not match.")
                return

            if not new_password:
                self.ui.print_error("Password cannot be empty.")
                return

            current_user.update_password(new_password)

            # Update in database
            try:
                self.database.update_entry(
                    "Users",
                    "password",
                    current_user.password.decode("utf-8"),
                    "userID",
                    current_user.userID,
                )
                self.database.update_entry(
                    "Users",
                    "passwordSalt",
                    current_user.passwordSalt.decode("utf-8")
                    if current_user.passwordSalt
                    else None,
                    "userID",
                    current_user.userID,
                )
            except Exception as e:
                logger.error(f"Failed to update password in database: {e}")

            logger.info(f"Password changed for user {current_user.username}")
            self.ui.print_success("Password changed successfully.")

        except KeyboardInterrupt:
            self.ui.print_warning("Password change cancelled.")
        except EOFError:
            self.ui.print_warning("Password change cancelled.")

    def whoami(self) -> None:
        """
        Display the current logged in user information.
        Args:
            None
        Returns:
            None
        """
        current_user = self.users.get(self.current_user)
        if current_user:
            role = "[bright_red]Admin[/]" if current_user.admin else "[white]User[/]"
            self.ui.print_info(
                f"Current user: [bright_cyan]{current_user.username}[/] ({role})"
            )
        else:
            self.ui.print_error("No user currently logged in.")
