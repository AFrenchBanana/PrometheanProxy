import ssl
import struct



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

def receive_data(conn: ssl.SSLSocket) -> str | bytes:
    """
    Receives data from a socket. The function handles receiving both the
    header and the actual data, attempting to decode it as UTF-8 if possible.
    """
    received_data = b''
    try:
        header = conn.recv(8)
        if not header:
            return b''
        
        total_length, chunk_size = struct.unpack('!II', header)
        
        while total_length > 0:
            chunk = conn.recv(min(chunk_size, total_length))
            if not chunk:
                break
            received_data += chunk
            total_length -= len(chunk)
            
        try:
            return received_data.decode("utf-8")
        except UnicodeDecodeError:
            return received_data
            
    except (struct.error, ConnectionError) as e:
        return b''