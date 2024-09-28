#!/usr/bin/python3

"""
initial file that starts the socket and multi handler
"""
import readline
import colorama
import sys
import threading

from Modules.multi_handler import MultiHandler
from Modules.global_objects import config
from Modules.http_server import connection, app

readline.parse_and_bind('tab: complete')

if __name__ == '__main__':
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()
        threading.Thread(target=app.run, kwargs={'port': 80},
                         daemon=True).start()
        multi_handler.startsocket()
        if not config['server']['quiet_mode']:
            print(colorama.Fore.CYAN + """
   ___                          _   _                        ___                     
  / _ \_ __ ___  _ __ ___   ___| |_| |__   ___  __ _ _ __   / _ \_ __ _____  ___   _ 
 / /_)/ '__/ _ \| '_ ` _ \ / _ \ __| '_ \ / _ \/ _` | '_ \ / /_)/ '__/ _ \ \/ / | | |
/ ___/| | | (_) | | | | | |  __/ |_| | | |  __/ (_| | | | / ___/| | | (_) >  <| |_| |
\/    |_|  \___/|_| |_| |_|\___|\__|_| |_|\___|\__,_|_| |_\/    |_|  \___/_/\_\\__ , |
                                                                               |___/ 
  """)
        else:
            print(colorama.Back.RED + "Quiet Mode On")
        print(colorama.Back.GREEN + "Type Help for available commands")
        multi_handler.multi_handler(config)  # starst the milti handler
    except ValueError:  # handles keyboard interpt
        print("\n use exit next time")
        sys.exit()
