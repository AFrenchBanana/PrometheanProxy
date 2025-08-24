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

def _extract_embedded_assets():
    """Ensure ~/.PrometheanProxy/config.toml exists and copy embedded plugins if bundled.

    - If running as a PyInstaller bundle, copy from embedded paths.
    - If running from source, copy default config from repo (src/Server/config.toml).
    """
    user_root = os.path.expanduser('~/.PrometheanProxy')
    os.makedirs(user_root, exist_ok=True)
    config_dst = os.path.join(user_root, 'config.toml')
    # Unified destination: put compiled modules and Python plugins under one root
    plugins_dst_root = os.path.join(user_root, 'plugins')
    os.makedirs(plugins_dst_root, exist_ok=True)

    base = getattr(sys, '_MEIPASS', None)
    if base:
        # Paths inside bundle as added by Makefile --add-data
        embedded_root = os.path.join(base, 'embedded')
        config_src = os.path.join(embedded_root, 'config.toml')
        # Compiled plugin artifacts staged by Makefile under embedded/plugins/<name>/{release,debug}
        plugins_root = os.path.join(embedded_root, 'plugins')
        # Python plugin sources staged by Makefile under embedded/pyplugins
        pyplugins_src = os.path.join(embedded_root, 'pyplugins')

        # Copy config.toml if missing
        try:
            if os.path.isfile(config_src) and not os.path.exists(config_dst):
                shutil.copy2(config_src, config_dst)
        except Exception:
            pass

        # Copy compiled plugin artifacts into unified layout:
        # ~/.PrometheanProxy/plugins/<name>/{release|debug}/<name>[ -debug].{so|dll}
        try:
            if os.path.isdir(plugins_root):
                for plugin_name in os.listdir(plugins_root):
                    pdir = os.path.join(plugins_root, plugin_name)
                    if not os.path.isdir(pdir):
                        continue
                    for channel in ("release", "debug"):
                        src_dir = os.path.join(pdir, channel)
                        if not os.path.isdir(src_dir):
                            continue
                        out_dir = os.path.join(plugins_dst_root, plugin_name, channel)
                        os.makedirs(out_dir, exist_ok=True)
                        for fname in os.listdir(src_dir):
                            src = os.path.join(src_dir, fname)
                            if not os.path.isfile(src):
                                continue
                            dst = os.path.join(out_dir, fname)
                            try:
                                shutil.copy2(src, dst)
                            except Exception:
                                pass
        except Exception:
            pass

        # Copy Python plugin sources to ~/.PrometheanProxy/plugins (preserve structure)
        try:
            if os.path.isdir(pyplugins_src):
                for root, dirs, files in os.walk(pyplugins_src):
                    rel = os.path.relpath(root, pyplugins_src)
                    rel_out = "" if rel == "." else rel
                    dst_root = os.path.join(plugins_dst_root, rel_out)
                    os.makedirs(dst_root, exist_ok=True)
                    for fname in files:
                        src = os.path.join(root, fname)
                        dst = os.path.join(dst_root, fname)
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            pass
        except Exception:
            pass
    else:
        # Running from source: copy default config from repo if missing
        repo_config = os.path.join(os.path.dirname(__file__), 'config.toml')
        try:
            if os.path.isfile(repo_config) and not os.path.exists(config_dst):
                shutil.copy2(repo_config, config_dst)
        except Exception:
            pass

        try:
            legacy_root = os.path.join(user_root, 'plugins', 'Plugins')
            if os.path.isdir(legacy_root):
                for name in os.listdir(legacy_root):
                    src_dir = os.path.join(legacy_root, name)
                    dst_dir = os.path.join(plugins_dst_root, name)
                    if os.path.isdir(src_dir):
                        for root, dirs, files in os.walk(src_dir):
                            rel = os.path.relpath(root, src_dir)
                            out_root = os.path.join(dst_dir, rel)
                            os.makedirs(out_root, exist_ok=True)
                            for fname in files:
                                try:
                                    shutil.copy2(os.path.join(root, fname), os.path.join(out_root, fname))
                                except Exception:
                                    pass
                try:
                    shutil.rmtree(legacy_root)
                except Exception:
                    pass
        except Exception:
            pass


_extract_embedded_assets()

# Defer heavy imports that rely on config until after extraction
from Modules.multi_handler.multi_handler import MultiHandler
from Modules.global_objects import config, logger
from Modules.beacon.beacon_server.server import start_beacon_server


logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

readline.parse_and_bind('tab: complete')

if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Starting server...")
    try:
        multi_handler = MultiHandler()

        logger.debug("Server: Starting beacon server thread")

        # --- Beacon Server Thread ---
        threading.Thread(
            target=start_beacon_server,
            args=(config,),
            daemon=True
        ).start()


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
