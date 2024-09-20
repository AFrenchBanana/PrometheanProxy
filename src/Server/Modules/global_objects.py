"""
Global Objects that are allowed to be accessed anywhere within the project.
This allows for a single form of management with items such as
connected sockets and the ability alter them.

Contains error handled send and recieve functions that
can handle bytes and strings
"""

from .content_handler import TomlFiles
import struct
from tqdm import tqdm
from typing import Tuple
import os
import ssl

# global socket details to alllow multiple connections and the ability
# to interact with them individually.
connectionaddress = []
connectiondetails = []
hostname = []
operatingsystem = []

try:
    with TomlFiles("config.toml") as f:
        config = f
except FileNotFoundError:
    with TomlFiles("src/Server/config.toml") as f:
        config = f


def add_connection_list(conn: ssl.SSLSocket,
                        r_address: Tuple[str, int],
                        host: str,
                        OS: str) -> None:
    """
    this function places the connection details into 3 lists, one for
    each variable upon succesful socket connection
    this allows the connection to be accessed from anywhere within the server
    """
    connectiondetails.append(conn)  # the socket connection details
    connectionaddress.append(r_address)  # the ip address and port
    hostname.append(host)  # hostname or the socke
    hostname.append(OS)  # hostname or the socket
    return


def remove_connection_list(r_address: Tuple[str, int]) -> None:
    """removes connection from all list.
    loops through the known connections and if it matches removes it"""
    for i, item in enumerate(
            connectionaddress):  # loops through connectionaddress list
        if item == r_address:  # if item matches the r_address fed in
            # removes the index number of connection details
            connectiondetails.pop(i)
            # removes the index number of connection address
            connectionaddress.pop(i)
            hostname.pop(i)  # removes the index number of the hostname
            operatingsystem.pop(i)
    return


def send_data(conn: ssl.SSLSocket, data: any) -> None:
    """function that sends data across a socket,
    socket connection and data gets fed in, the length
    of data is then calculated.
    the socket sends a header file packed with struct that
    sends the total length and chunk size
    The data is sent in chunks of 4096 until the last chunk
    where only the required amount is sent.
    the function allows for raw bytes and strings to be
    sent for multiple data types to be sent.
    """
    total_length = len(data)  # calculates the total length
    chunk_size = 4096  # sets the chunk size
    # sends a header with total_length and chunksize
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    for i in range(
            0,
            total_length,
            chunk_size):  # range of total length incrementing in chunksize
        # calculates how much data needs to be sent
        end_index = (i + chunk_size if
                     i + chunk_size < total_length else total_length)
        # makes the chunk with the required amount of data
        chunk = data[i:end_index]
        try:
            # trys to encode the chunks and send them
            conn.sendall(chunk.encode())
        except AttributeError:
            conn.sendall(chunk)  # if it cant be encoded sends it as it is.
    return


def receive_data(conn: ssl.SSLSocket) -> str | bytes:
    """
    function that recieves data
    first the header is recieved with the chunk size and total length
    after this it recieves data in the chunk size until the last packet
    where it is the remaining length
    """
    received_data = b''
    try:
        total_length, chunk_size = struct.unpack(
            '!II', conn.recv(8))
        while total_length > 0:
            chunk = conn.recv(min(chunk_size, total_length))
            received_data += chunk
            total_length -= len(chunk)
        try:
            received_data = received_data.decode(
                "utf-8")
        except UnicodeDecodeError:
            pass
    except struct.error:
        pass
    return received_data


def send_data_loadingbar(conn: ssl.SSLSocket, data: any) -> None:
    """
    function that sends data across a socket,
    socket connection and data gets fed in, the length
    of data is then calculated.
    The socket sends a header file packed with struct
    that sends the total length and chunk size
    The data is sent in chunks of 4096 until the last
    chunk where only the required amount is sent.
    the function allows for raw bytes and strings to be
    sent for multiple data types to be sent.
    This function has a built in loading bar
    to track how much of teh data has been sent.
    """
    total_length = len(data)
    chunk_size = 4096
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    for i in tqdm(
            range(
                0,
                total_length,
                chunk_size),
            desc="DataSent",
            colour="#39ff14"):
        end_index = (i + chunk_size if
                     i + chunk_size < total_length else total_length)
        chunk = data[i:end_index]
        try:
            conn.sendall(chunk.encode())
        except AttributeError:
            conn.sendall(chunk)
    return


def execute_local_comands(value: str) -> bool:
    """function that allows for the execution of local commands server side"""
    if value.lower().startswith(("ls", "cat", "pwd", "ping", "curl",
                                 "whoami", "\\", "clear")):  # common commands
        if value.startswith("\\"):  # other commands
            value = value.replace("\\", "")
        os.system(value)
        return True
    else:
        return None


def tab_compeletion(text: str, state: int, variables: list) -> str:
    """function that allows for tab completion in the config menu"""
    options = [var for var in variables if var.startswith(text)]
    return options[state] if state < len(options) else None
