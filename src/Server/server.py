#!/usr/bin/python3

"""
Initial file that starts the socket and multi handler.
"""
import readline
import colorama
import sys
import threading
import random
import traceback
import logging
import io
import time


from Modules.multi_handler.multi_handler import MultiHandler
from Modules.global_objects import config, logger
from Modules.beacon.beacon_server.server import start_beacon_server
from Modules.multiplayer.multiplayer import MultiPlayer

logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

readline.parse_and_bind('tab: complete')

if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Starting server...")
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()

        logger.debug("Server: Starting beacon server thread")

        # --- Beacon Server Thread ---
        threading.Thread(
            target=start_beacon_server,
            args=(config,),
            daemon=True
        ).start()

        logger.debug("Server: Starting web UI server thread")

        time.sleep(0.1) 

        multi_handler.startsocket()
        logger.debug("Server: Background server threads started successfully")

        if not config['server']['quiet_mode']:
            colors = [colorama.Fore.CYAN, colorama.Fore.RED,
                      colorama.Fore.GREEN, colorama.Fore.YELLOW,
                      colorama.Fore.BLUE]
            art_key = f'art{random.randint(1, 5)}'
            logger.info(f"Server: Displaying ASCII art with key {art_key}")
            print(random.choice(colors) + config['ASCII'][art_key])
        else:
            print(colorama.Back.RED + "Quiet Mode On")

        if config['server']['multiplayer']:
            multiplayer = MultiPlayer(config)
            print(colorama.Fore.GREEN + "Multiplayer mode enabled")
            logger.info("Server: Multiplayer mode enabled")
            threading.Thread(target=multiplayer.start(),
            args=(config,),
            daemon=True
        ).start()

        print(colorama.Back.GREEN + "Type Help for available commands")
        multi_handler.multi_handler(config)

    except Exception as e:
        logger.error(f"Server: Error occurred - {e}")
        print(colorama.Fore.RED + f"Error: {e}")
        if not config['server']['quiet_mode']:
            print(colorama.Fore.RED + "Traceback:")
            traceback.print_exc()
        print("\nUse 'exit' or 'quit' next time.")
        logger.critical("Server: Exiting due to error")
        sys.exit()
