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
import os
import shutil

from Modules.multi_handler.multi_handler import MultiHandler
from Modules.global_objects import config, logger
from Modules.beacon.beacon_server.server import start_beacon_server

def _extract_embedded_assets():
    """When packaged with PyInstaller, extract config.toml and plugins to user dir."""
    base = getattr(sys, '_MEIPASS', None)
    if not base:
        return
    # Paths inside bundle as added by Makefile --add-data
    embedded_root = os.path.join(base, 'embedded')
    config_src = os.path.join(embedded_root, 'config.toml')
    plugins_linux_rel = os.path.join(embedded_root, 'plugins', 'linux', 'release')
    plugins_linux_dbg = os.path.join(embedded_root, 'plugins', 'linux', 'debug')

    # Targets
    user_root = os.path.expanduser('~/.PrometheanProxy')
    os.makedirs(user_root, exist_ok=True)
    config_dst = os.path.join(user_root, 'config.toml')
    modules_dst_root = os.path.join(user_root, 'modules')
    os.makedirs(modules_dst_root, exist_ok=True)

    # Copy config.toml if missing
    try:
        if os.path.isfile(config_src) and not os.path.exists(config_dst):
            shutil.copy2(config_src, config_dst)
    except Exception:
        pass

    # Copy plugins (overwrite to keep updated)
    mapping = [
        (plugins_linux_rel, os.path.join(modules_dst_root, 'linux', 'release')),
        (plugins_linux_dbg, os.path.join(modules_dst_root, 'linux', 'debug')),
    ]
    for src_dir, dst_dir in mapping:
        if os.path.isdir(src_dir):
            os.makedirs(dst_dir, exist_ok=True)
            for fname in os.listdir(src_dir):
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass


_extract_embedded_assets()


logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

readline.parse_and_bind('tab: complete')

if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Starting server...")
    try:
        _extract_embedded_assets()
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
