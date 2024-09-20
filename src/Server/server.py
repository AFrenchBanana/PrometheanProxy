#!/usr/bin/python3

"""
initial file that starts the socket and multi handler
"""
import readline
import colorama
import sys

from Modules.multi_handler import MultiHandler
from Modules.global_objects import config

readline.parse_and_bind('tab: complete')

if __name__ == '__main__':
    try:
        multi_handler = MultiHandler()
        multi_handler.create_certificate()
        multi_handler.startsocket()
        if not config['server']['quiet_mode']:
            print(colorama.Fore.CYAN + """
        CCCCCCCCCCCCC 222222222222222
      CCC::::::::::::C2:::::::::::::::22
    CC:::::::::::::::C2::::::222222:::::2
  C:::::CCCCCCCC::::C2222222     2:::::2
  C:::::C       CCCCCC            2:::::2
  C:::::C                          2:::::2
  C:::::C                       2222::::2
  C:::::C                  22222::::::22
  C:::::C                22::::::::222
  C:::::C               2:::::22222
  C:::::C              2:::::2
  C:::::C       CCCCCC2:::::2
  C:::::CCCCCCCC::::C2:::::2       222222
    CC:::::::::::::::C2::::::2222222:::::2
      CCC::::::::::::C2::::::::::::::::::2
        CCCCCCCCCCCCC22222222222222222222
  """)
        else:
            print(colorama.Back.RED + "Quiet Mode On")
        print(colorama.Back.GREEN + "Type Help for available commands")
        multi_handler.multi_handler(config)  # starst the milti handler
    except ValueError:  # handles keyboard interpt
        print("\n use exit next time")
        sys.exit()
