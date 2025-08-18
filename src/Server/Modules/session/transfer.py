# Modules/session/transfer.py

import ssl
import struct
import os
import hmac
import hashlib
from typing import Optional, Tuple, Dict
from tqdm import tqdm
from ..global_objects import logger

# App-layer crypto: ECDH (X25519) + AES-GCM
try:
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception as _e:  # cryptography might not be installed yet
    x25519 = None  # type: ignore
    HKDF = None  # type: ignore
    hashes = None  # type: ignore
    AESGCM = None  # type: ignore

# Per-connection symmetric keys derived post-SSL using ECDH
_CONN_KEYS: Dict[int, Tuple[Optional[bytes], Optional[bytes]]] = {}
_KEX_MAGIC = b"PPKX\x01"  # 5-byte preface + version

def _recv_exact(conn: ssl.SSLSocket, n: int) -> bytes:
    """
    Receive exactly n bytes or raise ConnectionError if the connection closes.
    """
    buf = b''
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f"Expected {n} bytes, got {len(buf)} before connection closed.")
        buf += chunk
    return buf


def _derive_key(shared_secret: bytes) -> Tuple[bytes, bytes]:
    """Derive separate 256-bit keys (enc_key, mac_key) via HKDF-SHA256."""
    if HKDF is None or hashes is None:
        raise RuntimeError("cryptography library is required for ECDH/AES-GCM")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=None,
        info=b"PrometheanProxy/MP_ECDH_v1",
    )
    out = hkdf.derive(shared_secret)
    return out[:32], out[32:]


def perform_ecdh_handshake(conn: ssl.SSLSocket, is_server: bool) -> bytes:
    """
    Perform an ECDH (X25519) handshake over the established SSL socket to agree a
    symmetric key for AES-GCM. The derived key is cached per-connection and returned.

    Wire format:
      Server -> Client:  PPKX\x01 || server_pub (32B)
      Client -> Server:  client_pub (32B)
    """
    if x25519 is None:
        raise RuntimeError("cryptography library is required for ECDH/AES-GCM")

    priv = x25519.X25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    if is_server:
        conn.sendall(_KEX_MAGIC + pub_bytes)
        client_pub = _recv_exact(conn, 32)
        peer_pub = x25519.X25519PublicKey.from_public_bytes(client_pub)
    else:
        preface = _recv_exact(conn, len(_KEX_MAGIC))
        if preface != _KEX_MAGIC:
            raise ConnectionError("Invalid ECDH preface from server")
        server_pub = _recv_exact(conn, 32)
        conn.sendall(pub_bytes)
        peer_pub = x25519.X25519PublicKey.from_public_bytes(server_pub)

    shared = priv.exchange(peer_pub)
    enc_key, mac_key = _derive_key(shared)
    _CONN_KEYS[id(conn)] = (enc_key, mac_key)
    logger.debug("ECDH handshake complete; session key established for connection")
    return enc_key


def _get_keys(conn: ssl.SSLSocket) -> Tuple[Optional[bytes], Optional[bytes]]:
    return _CONN_KEYS.get(id(conn), (None, None))


def send_data_signed(conn: ssl.SSLSocket, payload: bytes) -> None:
    """Encrypt (if key present) and HMAC-sign each message; then frame and send.
    Layouts:
      With enc+mac: [4B len blob] [blob=nonce(12)+ciphertext] [32B HMAC(blob)]
      With only mac: [4B len payload] [payload] [32B HMAC(payload)]
      With no keys: [4B len payload] [payload]
    """
    enc_key, mac_key = _get_keys(conn)
    if enc_key:
        if AESGCM is None:
            raise RuntimeError("cryptography library is required for AES-GCM")
        aes = AESGCM(enc_key)
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, payload, None)
        blob = nonce + ct
        conn.sendall(struct.pack("!I", len(blob)))
        conn.sendall(blob)
        if mac_key:
            tag = hmac.new(mac_key, blob, hashlib.sha256).digest()
            conn.sendall(tag)
        return

    # No encryption
    conn.sendall(struct.pack("!I", len(payload)))
    conn.sendall(payload)
    if mac_key:
        tag = hmac.new(mac_key, payload, hashlib.sha256).digest()
        conn.sendall(tag)

def send_data(conn: ssl.SSLSocket, data: any, key: Optional[bytes] = None) -> None:
    """
    Send data over the SSL socket. If a post-SSL ECDH key is configured for this
    connection (either provided or cached), encrypt using AES-GCM.
    Format when encrypted:
      [4-byte BE length of (nonce+ciphertext)] || nonce(12B) || ciphertext
    Fallback (no key): legacy simple framing [4-byte length] || payload.
    """
    if isinstance(data, str):
        payload = data.encode()
    else:
        payload = data

    # Route through signed sender; 'key' param kept for compat but ignored
    if isinstance(data, str):
        payload = data.encode()
    else:
        payload = data
    send_data_signed(conn, payload)
    logger.debug(f"Sent message ({len(payload)}B payload) with HMAC{' and AES-GCM' if _get_keys(conn)[0] else ''}")

def receive_data_signed(conn: ssl.SSLSocket) -> bytes:
    """Receive a framed message; verify HMAC if present; decrypt if encrypted."""
    enc_key, mac_key = _get_keys(conn)
    # Read primary framed part
    size_buf = _recv_exact(conn, 4)
    total_len = struct.unpack("!I", size_buf)[0]
    blob = _recv_exact(conn, total_len)

    # If a MAC key is present, a 32B tag must follow
    if mac_key:
        tag = _recv_exact(conn, 32)
        calc = hmac.new(mac_key, blob if enc_key else blob, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, calc):
            logger.error("HMAC verification failed for received message")
            return b''

    if enc_key:
        if len(blob) < 13:
            logger.error("Malformed encrypted payload")
            return b''
        nonce, ct = blob[:12], blob[12:]
        if AESGCM is None:
            raise RuntimeError("cryptography library is required for AES-GCM")
        aes = AESGCM(enc_key)
        try:
            return aes.decrypt(nonce, ct, None)
        except Exception as e:
            logger.error(f"AES-GCM decryption failed: {e}")
            return b''

    # Plaintext path
    return blob


def receive_data(conn: ssl.SSLSocket, key: Optional[bytes] = None) -> str | bytes:
    """
    Receive data framed over the SSL socket. If an ECDH key is configured for this
    connection, decrypt using AES-GCM. Otherwise, fallback to plain framing.
    Returns bytes or UTF-8 string if decodable.
    """
    try:
        received_data = receive_data_signed(conn)
        try:
            return received_data.decode("utf-8")
        except UnicodeDecodeError:
            return received_data

    except (struct.error, ConnectionError) as e:
        logger.error(f"Failed to receive data: {e}")
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