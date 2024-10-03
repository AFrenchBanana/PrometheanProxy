import readline

from .content_handler import TomlFiles
from .global_objects import tab_completion
import ipaddress

CONFIG_FILE_PATH = 'config.toml'


def config_menu() -> None:
    while True:
        print("Config Menu")
        print("1. Show Config")
        print("2. Edit Config")
        print("3. Exit")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, [
                    "1", "2", "3"]))
        inp = input("Enter Option: ")
        if inp == "1":
            show_config()
        if inp == "2":
            edit_config()
        if inp == "3":
            return


def show_config() -> None:
    """Shows the config TOML configuration"""
    config = ""
    with open(CONFIG_FILE_PATH, "r") as f:
        file = f.readlines()
    for line in file:
        if line.startswith("[MultiHandlerCommands]"):
            break
        config += line
    print(config)


def edit_config() -> bool:
    main_keys = ["server", "authentication", "packetsniffer", "exit"]
    server_keys = [
        "listenaddress",
        "port",
        "TLSCertificateDir",
        "TLSCertificate",
        "TLSkey",
        "GUI",
        "quiet_mode"]
    authentication_keys = ["keylength"]
    packetsniffer_keys = [
        "active",
        "listenaddress",
        "port",
        "TLSCertificate",
        "TLSKey",
        "debugPrint"]
    toml_file = TomlFiles(CONFIG_FILE_PATH)
    with toml_file as config:
        while True:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(
                lambda text, state: tab_completion(
                    text, state, main_keys))
            key = input("Enter key: ")
            if key == "exit":
                return False
            if key not in main_keys:
                print("Not a valid key")
                pass
            if key == "server":
                readline.parse_and_bind("tab: cowmplete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, server_keys))
            elif key == "authentication":
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, authentication_keys))
            elif key == "packetsniffer":
                readline.parse_and_bind("tab: complete")
                readline.set_completer(
                    lambda text, state: tab_completion(
                        text, state, packetsniffer_keys))
            subkey = input("Enter sub-key to change: ")
            if subkey not in config[key]:
                print("Invalid subkey")
                pass
            print("Current value: ", config[key][subkey])
            new_value = input("Enter new value: ")
            if isinstance(config[key][subkey], bool):
                if new_value.lower() not in ["true", "false"]:
                    print("Invalid value. Please enter true or false")
                else:
                    update = True
                    if new_value.lower() == "true":
                        new_value = True
                    else:
                        new_value = False
            elif isinstance(config[key][subkey], int):
                if not new_value.isdigit():
                    print("Invalid value. Please enter a number")
                else:
                    update = True
            elif subkey == ("listenaddress" and not
                            ipaddress.ip_address(new_value)):
                print("Invalid value. Please enter a valid IP address")
            elif (subkey == "port" and not new_value.isdigit() and
                  (int(new_value) < 0 or int(new_value) > 65535)):
                print("Invalid value. Please enter a valid port number")
                continue
            else:
                update = True
            if update:
                toml_file.update_config(key, subkey, new_value)
                print("Changes saved successfully!")
                print("Restart the server to apply changes.")
                return True
