from ..global_objects import logger
from .mp_socket import MP_Socket

class MultiPlayer (MP_Socket):
    """
    This class extends MP_Socket to handle multiplayer functionality.
    It inherits the socket management and SSL handling from MP_Socket.
    """
    def __init__(self, config):
        super().__init__(config)
        # self.database = DatabaseClass(config['server']['database'])
        logger.info("MultiPlayer instance created with database connection")
    
    def start(self):
        super().start()
        logger.info("Multiplayer server started and listening for connections")