import json
import time
import uuid
import ssl
import struct
import os
import hmac
import hashlib
from typing import Optional, Tuple, Dict

# App-layer crypto (post-SSL): ECDH (X25519) + AES-GCM
try:
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    x25519 = None  # type: ignore
    HKDF = None  # type: ignore
    hashes = None  # type: ignore
    AESGCM = None  # type: ignore

_CONN_KEYS: Dict[int, Tuple[Optional[bytes], Optional[bytes]]] = {}
_KEX_MAGIC = b"PPKX\x01"

def send_data_json(conn: ssl.SSLSocket, auth_key: str, command: str, args: dict) -> None:
    """
    Sends JSON data across a socket.
    """
    json_data = json.dumps({
        "id": uuid.uuid4().hex,
        "authorization": auth_key,
        "session_uuid": uuid.uuid4().hex,
        "timestamp": time.time(),
        "command": command,
        "args": args
    }).encode('utf-8')
    send_data(conn, json_data)

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
    if x25519 is None:
        raise RuntimeError("cryptography library is required for ECDH/AES-GCM")
    priv = x25519.X25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if is_server:
        conn.sendall(_KEX_MAGIC + pub_bytes)
        peer_pub = _recv_exact(conn, 32)
        peer = x25519.X25519PublicKey.from_public_bytes(peer_pub)
    else:
        preface = _recv_exact(conn, len(_KEX_MAGIC))
        if preface != _KEX_MAGIC:
            raise ConnectionError("Invalid ECDH preface from server")
        server_pub = _recv_exact(conn, 32)
        conn.sendall(pub_bytes)
        peer = x25519.X25519PublicKey.from_public_bytes(server_pub)
    enc_key, mac_key = _derive_key(priv.exchange(peer))
    _CONN_KEYS[id(conn)] = (enc_key, mac_key)
    return enc_key


def _get_keys(conn: ssl.SSLSocket) -> Tuple[Optional[bytes], Optional[bytes]]:
    return _CONN_KEYS.get(id(conn), (None, None))


def send_data_signed(conn: ssl.SSLSocket, payload: bytes) -> None:
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

    conn.sendall(struct.pack("!I", len(payload)))
    conn.sendall(payload)
    if mac_key:
        tag = hmac.new(mac_key, payload, hashlib.sha256).digest()
        conn.sendall(tag)

def send_data(conn: ssl.SSLSocket, data: any, key: Optional[bytes] = None) -> None:
    if isinstance(data, str):
        payload = data.encode()
    else:
        payload = data
    send_data_signed(conn, payload)

def receive_data_signed(conn: ssl.SSLSocket) -> bytes:
    enc_key, mac_key = _get_keys(conn)
    size_buf = _recv_exact(conn, 4)
    total_len = struct.unpack("!I", size_buf)[0]
    blob = _recv_exact(conn, total_len)
    if mac_key:
        tag = _recv_exact(conn, 32)
        ref = blob
        calc = hmac.new(mac_key, ref, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, calc):
            return b''
    if enc_key:
        if AESGCM is None:
            raise RuntimeError("cryptography library is required for AES-GCM")
        if len(blob) < 13:
            return b''
        nonce, ct = blob[:12], blob[12:]
        aes = AESGCM(enc_key)
        return aes.decrypt(nonce, ct, None)
    return blob


def receive_data(conn: ssl.SSLSocket, key: Optional[bytes] = None) -> str | bytes:
    try:
        payload = receive_data_signed(conn)
        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return payload
    except (struct.error, ConnectionError):
        return b''