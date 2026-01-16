from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.box import ROUNDED
from rich.table import Table

from ..global_objects import logger
from ..utils.ui_manager import get_ui_manager
from .mp_server import MP_Socket
from .users.mp_users import MP_Users
from .web_interface import WebInterface


class MultiPlayer(MP_Socket, MP_Users):
    """
    This class extends MP_Socket to handle multiplayer functionality.
    It inherits the socket management and SSL handling from MP_Socket.
    """

    def __init__(self, config):
        MP_Socket.__init__(self, config)
        MP_Users.__init__(self, config)
        self.ui = get_ui_manager()
        self.menu_session = PromptSession()

        # Initialize web interface
        self.web_interface = WebInterface(config)

        logger.info("MultiPlayer instance created with database connection")

    def start(self):
        super().start()
        logger.info("Multiplayer server started and listening for connections")

        # Start web interface if enabled
        try:
            if self.web_interface.start():
                self.ui.print_success("Web interface started successfully")
            else:
                self.ui.print_info(
                    "Web interface not started (disabled or dependencies missing)"
                )
        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            self.ui.print_warning(
                "Web interface failed to start - continuing without it"
            )

    def currentUsers(self) -> str:
        """
        Returns a string representation of the current users in the multiplayer system.
        """
        return str(self.currentUserName)

    def _create_user_menu_table(self) -> Table:
        """Create a modern styled user menu table."""
        table = Table(
            title="[bold bright_magenta]◈ User Management Menu[/]",
            box=ROUNDED,
            border_style="bright_magenta",
            header_style="bold bright_white on purple4",
            padding=(0, 1),
            expand=False,
        )

        table.add_column("Option", style="bright_cyan", width=8, justify="center")
        table.add_column("Action", style="white")

        menu_items = [
            ("1", "Add User"),
            ("2", "Remove User"),
            ("3", "Change Password"),
            ("4", "List Users"),
            ("5", "Switch User"),
            ("6", "Who Am I"),
            ("7", "Exit Menu"),
        ]

        for opt, action in menu_items:
            table.add_row(f"[bright_yellow]{opt}[/]", action)

        return table

    def userMenu(self):
        """
        Interactive user management menu with modern UI styling.
        """
        menu_actions = {
            "1": ("add", self.add_user_input),
            "2": ("remove", self.remove_user_input),
            "3": ("password", self.change_password_input),
            "4": ("list", self.list_users),
            "5": ("switch", self.switch_user_input),
            "6": ("whoami", self.whoami),
            "7": ("exit", None),
        }

        # Create command completer for menu
        menu_completer = WordCompleter(
            [
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "add",
                "remove",
                "password",
                "list",
                "switch",
                "whoami",
                "exit",
            ],
            ignore_case=True,
        )

        while True:
            # Display current user info
            self.ui.print_info(f"Logged in as: [bright_cyan]{self.currentUsers()}[/]")

            # Display menu table
            menu_table = self._create_user_menu_table()
            self.ui.console.print(menu_table)

            try:
                choice = (
                    self.menu_session.prompt(
                        "[bright_magenta]>[/] Select option: ",
                        completer=menu_completer,
                    )
                    .strip()
                    .lower()
                )

                # Handle exit
                if choice in ("7", "exit", "q", "quit"):
                    self.ui.print_info("Exiting user menu...")
                    break

                # Find action by number or name
                action_func = None
                for key, (name, func) in menu_actions.items():
                    if choice == key or choice == name:
                        action_func = func
                        break

                if action_func:
                    action_func()
                elif choice:
                    self.ui.print_warning(f"Invalid option: [bright_cyan]{choice}[/]")

                # Add spacing between iterations
                self.ui.console.print()

            except KeyboardInterrupt:
                self.ui.print_warning("Menu interrupted.")
                break
            except EOFError:
                self.ui.print_info("Exiting user menu...")
                break

    def get_web_status(self) -> dict:
        """
        Get the current status of the web interface.

        Returns:
            dict: Web interface status information
        """
        return self.web_interface.get_status()

    def stop_web_interface(self):
        """Stop the web interface."""
        self.web_interface.stop()
