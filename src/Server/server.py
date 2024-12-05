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

from Modules.multi_handler import MultiHandler
from Modules.global_objects import config
from Modules.http_server import app

readline.parse_and_bind('tab: complete')

os.environ['FLASK_ENV'] = 'production'

if __name__ == '__main__':
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()
        threading.Thread(
            target=app.run, kwargs={'port': config["server"]["webPort"],
                                    'debug': False}, daemon=True).start()
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
        multi_handler.multi_handler(config)  # starst the milti handler
    except Exception as e:  # handles keyboard interrupt
        print(colorama.Fore.RED + f"Error: {e}")
        print("\n use exit next time")
        sys.exit()
