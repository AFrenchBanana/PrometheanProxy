# Modules/session/transfer.py

import ssl
import struct
from tqdm import tqdm
from ..global_objects import logger

def send_data(conn: ssl.SSLSocket, data: any) -> None:
    """
    Sends data across a socket. The function allows for raw bytes and strings
    to be sent for multiple data types.
    """
    if isinstance(data, str):
        data = data.encode()
        
    total_length = len(data)
    chunk_size = 4096
    
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    
    for i in range(0, total_length, chunk_size):
        end_index = min(i + chunk_size, total_length)
        chunk = data[i:end_index]
        conn.sendall(chunk)
        logger.debug(f"Sending raw chunk of size {len(chunk)}")

def receive_data(conn: ssl.SSLSocket) -> str | bytes:
    """
    Receives data from a socket. The function handles receiving both the
    header and the actual data, attempting to decode it as UTF-8 if possible.
    """
    received_data = b''
    try:
        logger.debug("Receiving data header")
        header = conn.recv(8)
        if not header:
            logger.warning("Connection closed while waiting for data header.")
            return b''
        
        total_length, chunk_size = struct.unpack('!II', header)
        
        while total_length > 0:
            chunk = conn.recv(min(chunk_size, total_length))
            if not chunk:
                logger.error("Connection closed prematurely during data reception.")
                break
            received_data += chunk
            total_length -= len(chunk)
            
        logger.debug(f"Received data of size {len(received_data)}")
        try:
            return received_data.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug("Received data could not be decoded as UTF-8, returning raw bytes")
            return received_data
            
    except (struct.error, ConnectionError) as e:
        logger.error(f"Failed to receive data, connection may be closed or invalid: {e}")
        return b''

def send_data_loadingbar(conn: ssl.SSLSocket, data: any) -> None:
    """
    Sends data across a socket with a loading bar to track progress.
    """
    logger.info("Sending data with loading bar")
    if isinstance(data, str):
        data = data.encode()

    total_length = len(data)
    chunk_size = 4096
    conn.sendall(struct.pack('!II', total_length, chunk_size))
    
    with tqdm(total=total_length, desc="Data Sent", unit="B", unit_scale=True, colour="#39ff14") as pbar:
        for i in range(0, total_length, chunk_size):
            end_index = min(i + chunk_size, total_length)
            chunk = data[i:end_index]
            conn.sendall(chunk)
            pbar.update(len(chunk))