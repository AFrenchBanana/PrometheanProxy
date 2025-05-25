#!/usr/bin/python3

"""
initial file that starts the socket and multi handler
"""
import readline
import colorama
import sys
import threading
import random
import os
import traceback

from Modules.multi_handler import MultiHandler
from Modules.global_objects import config, logger
from Modules.http_server import beaconControl, socketio as beaconSocketIO
from WebUI.http import app, socketio as webSocketIO

readline.parse_and_bind('tab: complete')

os.environ['FLASK_ENV'] = 'production'

if __name__ == '__main__':
    logger.info("Starting server...")
    try:
        logger.debug("Server: Initializing colorama")
        multi_handler = MultiHandler()
        multi_handler.create_certificate()
        logger.debug("Server: Starting socket and web server threads")
        threading.Thread(
            target=beaconSocketIO.run,
            args=(beaconControl,),
            kwargs={
                'port': config["server"]["webPort"],
                'debug': not config['server']['quiet_mode'],
                'use_reloader': False
            },
            daemon=True).start()
        threading.Thread(
            target=webSocketIO.run,
            args=(app,),
            kwargs={
                'port': 9000,
                'debug': not config['server']['quiet_mode'],
                'use_reloader': False
            },
            daemon=True
        ).start()
        multi_handler.startsocket()
        logger.debug("Server: Socket and web server threads started successfully")
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
        print("\n use exit next time")
        logger.critical("Server: Exiting due to error")
        sys.exit()
