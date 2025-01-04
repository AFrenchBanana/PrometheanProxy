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

beacon_list = {}
command_list = {}
sessions_list = {}


class session:
    def __init__(self, address, details, hostname, operating_system, mode):
        self.address = address
        self.details = details
        self.hostname = hostname
        self.operating_system = operating_system
        self.mode = mode


class beacon:
    def __init__(self, address, hostname, operating_system,
                 last_beacon, timer, jitter):
        self.address = address
        self.hostname = hostname
        self.operating_system = operating_system
        self.last_beacon = last_beacon
        self.next_beacon = str(last_beacon) + str(timer)
        self.timer = timer
        self.jitter = jitter


class beacon_command:
    def __init__(self, beacon_uuid, command, command_output,
                 executed, command_data):
        self.beacon_uuid = beacon_uuid
        self.command = command
        self.command_output = command_output
        self.executed = executed
        self.command_data = command_data


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
    new_session = session(r_address, conn, host, operating_system, mode)
    sessions_list[user_id] = new_session


def add_beacon_list(uuid: str, r_address: str, hostname: str,
                    operating_system: str, last_beacon, timer,
                    jitter) -> None:
    new_beacon = beacon(
        r_address, hostname, operating_system, last_beacon, timer, jitter
    )
    beacon_list[uuid] = new_beacon


def add_beacon_command_list(beacon_uuid: str,
                            command: str, command_data: json = {}) -> None:
    command_uuid = str(uuid.uuid4())
    new_command = beacon_command(beacon_uuid, command, "", False, command_data)
    command_list[command_uuid] = new_command


def remove_connection_list(r_address: Tuple[str, int]) -> None:
    """
    Removes connection from the global connections dictionary.
    """
    for key, value in sessions_list.items():
        if value.address == r_address:
            sessions_list.pop(key)
            break
    else:
        print(f"Connection {r_address} not found in sessions list")


def remove_beacon_list(uuid: str) -> None:
    """
    Removes beacon from the global beacon dictionary.
    """
    if uuid in beacon_list:
        beacon_list.pop(uuid)
    else:
        print(f"Beacon {uuid} not found in beacon list")


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
