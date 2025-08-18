from ..global_objects import logger
from .mp_socket import MP_Socket
from .mp_users import MP_Users

class MultiPlayer (MP_Socket, MP_Users):
    """
    This class extends MP_Socket to handle multiplayer functionality.
    It inherits the socket management and SSL handling from MP_Socket.
    """
    def __init__(self, config):
        MP_Socket.__init__(self, config)
        MP_Users.__init__(self, config)
        # self.database = DatabaseClass(config['server']['database'])
        logger.info("MultiPlayer instance created with database connection")
    
    def start(self):
        super().start()
        logger.info("Multiplayer server started and listening for connections")

    def currentUsers(self) -> str:
        """
        Returns a string representation of the current users in the multiplayer system.
        """
        return str(self.currentUser())
        
    def userMenu(self):
        menu_actions = {
            "1": lambda: self.add_user_input(),
            "2": lambda: print("Remove User selected"),
            "3": lambda: print("Update User Password selected"),
            "4": lambda: print(self.list_users()),
            "5": lambda: self.switch_user_input(),
            "6": lambda: print("Exiting User Menu")
        }
        print(f"""
              You you are logged in as {self.currentUsers()}:
              1. Add User
              2. Remove User
              3. Update User Password
              4. List Users 
              5. Switch User
              6. Exit User Menu
              """
              )
        choice = input("Select an option: ").strip()
        action = menu_actions.get(choice, lambda: print("Invalid option"))
        action()
        
