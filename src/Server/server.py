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
from Modules.global_objects import config
from Modules.http_server import beaconControl, socketio as beaconSocketIO
from WebUI.http import app, socketio as webSocketIO

readline.parse_and_bind('tab: complete')

os.environ['FLASK_ENV'] = 'production'

if __name__ == '__main__':
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()
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
        if not config['server']['quiet_mode']:
            colors = [colorama.Fore.CYAN, colorama.Fore.RED,
                      colorama.Fore.GREEN, colorama.Fore.YELLOW,
                      colorama.Fore.BLUE]
            art_key = f'art{random.randint(1, 5)}'
            print(random.choice(colors) + config['ASCII'][art_key])
        else:
            print(colorama.Back.RED + "Quiet Mode On")
        print(colorama.Back.GREEN + "Type Help for available commands")
        multi_handler.multi_handler(config) 
    except Exception as e: 
        print(colorama.Fore.RED + f"Error: {e}")
        if not config['server']['quiet_mode']:
            print(colorama.Fore.RED + "Traceback:")
            traceback.print_exc()
        print("\n use exit next time")
        sys.exit()
