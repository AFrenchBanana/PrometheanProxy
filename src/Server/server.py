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
from WebUI.http import app, socketio as webSocketIO

logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

readline.parse_and_bind('tab: complete')

if __name__ == '__main__':
    logger.info("Starting server...")
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()

        logger.debug("Server: Starting beacon server and web UI server threads")

        # --- Beacon Server Thread ---
        threading.Thread(
            target=start_beacon_server,
            args=(config,),
            daemon=True
        ).start()

        # --- WebUI Server Thread ---
        webui_kwargs = {
            'host': '0.0.0.0',
            'port': 9000,
            'debug': not config['server']['quiet_mode'],
            'use_reloader': False,
            'allow_unsafe_werkzeug': True
        }
        old_stdout = sys.stdout  # horrible hack to suppress output
        sys.stdout = io.StringIO()

        threading.Thread(
            target=webSocketIO.run,
            args=(app,),
            kwargs=webui_kwargs,
            daemon=True
        ).start()

        time.sleep(0.5)
        sys.stdout = old_stdout

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
