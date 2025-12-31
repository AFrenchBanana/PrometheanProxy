import os
import ssl
import json
import threading
import secrets
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from flask import Flask, request, jsonify

from ..global_objects import logger, multiplayer_connections, beacon_list, sessions_list
from ..utils.console import cprint, warn, error as c_error


@dataclass
class HTTPClientSession:
    """Represents an authenticated HTTP multiplayer client session."""
    username: str
    token: str
    address: tuple
    is_authenticated: bool = True


class MP_Socket:  # Keeping the original class name for compatibility
    """HTTP (TLS) based multiplayer control server.

    Endpoints:
        POST /api/login {username, password} -> returns auth token
        GET  /api/status -> user + auth status
        GET  /api/connections -> active beacons/sessions
        GET  /api/commands?uuid=UUID -> available commands for implant/session
        POST /api/logout -> invalidate current token
    Authentication: Provide token via Authorization: Bearer <token> header or ?token= query parameter.
    Token Model (updated):
        One active token per user. Re-authentication rotates the token; any previous token
        for that user becomes invalid immediately. Internally we store a username->token map
        plus a reverse index for O(1) token->username lookups.
    """

    def __init__(self, config):
        self.config = config
        self.port = config['multiplayer']['multiplayerPort']
        if not (isinstance(self.port, int) and 1 <= self.port <= 65535):
            logger.error(f"Invalid port number: {self.port}. Must be between 1 and 65535.")
            raise ValueError("Invalid port number")

        self.address = (
            self.config['multiplayer']['multiplayerListenAddress'],
            self.config['multiplayer']['multiplayerPort']
        )
        self._app = Flask("PrometheanProxy-Multiplayer")
        # Per-user token store: username -> {token: str, expires: datetime}
        self._user_tokens = {}
        # Reverse index for quick token -> username lookup (only currently valid tokens)
        self._token_index = {}
        self._tokens_lock = threading.Lock()
        # Token TTL (seconds) - default 1 week; allow config override multiplayer.tokenTTLSeconds
        ttl_cfg = self.config.get('multiplayer', {}).get('tokenTTLSeconds') if isinstance(self.config, dict) else None
        try:
            self._token_ttl = int(ttl_cfg) if ttl_cfg else 7 * 24 * 60 * 60
        except (TypeError, ValueError):
            self._token_ttl = 7 * 24 * 60 * 60
        self._register_routes()
        logger.info("Initialised HTTP multiplayer server (per-user token model)")
        

    def _gen_token(self) -> str:
        return secrets.token_hex(24)

    def _get_token(self):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(None, 1)[1].strip()
        return request.args.get("token") or request.cookies.get("pp_token")

    def _require_auth(self):
        token = self._get_token()
        if not token:
            return None
        with self._tokens_lock:
            username = self._token_index.get(token)
            if not username:
                return None
            record = self._user_tokens.get(username)
            if not record or record.get('token') != token:
                # Stale mapping; cleanup just in case
                self._token_index.pop(token, None)
                return None
            expires: datetime = record.get('expires')
            if expires and datetime.now(timezone.utc) >= expires:
                # Expired token: remove
                self._token_index.pop(token, None)
                self._user_tokens.pop(username, None)
                logger.info(f"Expired token for user {username} rejected")
                return None
            return username

    def _issue_token(self, username: str) -> dict:
        """Generate and store a new token (rotating any previous) for a user.
        Returns dict with token and expiry ISO string."""
        new_token = self._gen_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._token_ttl)
        # Rotate existing
        old_record = self._user_tokens.get(username)
        if old_record:
            old_token = old_record.get('token')
            if old_token:
                self._token_index.pop(old_token, None)
        self._user_tokens[username] = {"token": new_token, "expires": expires_at}
        self._token_index[new_token] = username
        return {"token": new_token, "expires": expires_at.isoformat()}

    def _available_commands(self, implant_uuid: str):
        available_commands = {"beacon": ["test"], "session": ["test2"]}
        for userID, beacon in beacon_list.items():
            beacon_uuid = getattr(beacon, "uuid", None) or userID
            if beacon_uuid == implant_uuid:
                mode = getattr(beacon, "mode", "beacon")
                return available_commands.get(mode, available_commands.get("beacon"))
        for userID, session in sessions_list.items():
            session_uuid = getattr(session, "uuid", None) or userID
            if session_uuid == implant_uuid:
                mode = getattr(session, "mode", "session")
                return available_commands.get(mode, available_commands.get("session"))
        return {"error": "Invalid UUID"}

    def _get_active_connections(self, filter):
        logger.debug(f"Fetching active connections with filter: {filter}")
        beacons = []
        sessions = []
        if filter == "beacons" or filter is None:
            for userID, beacon in beacon_list.items():
                beacons.append({
                    "userID": userID,
                    "uuid": getattr(beacon, "uuid", None),
                    "address": getattr(beacon, "address", None),
                    "hostname": getattr(beacon, "hostname", None),
                    "operating_system": getattr(beacon, "operating_system", None),
                    "last_beacon": getattr(beacon, "last_beacon", None),
                    "next_beacon": getattr(beacon, "next_beacon", None),
                    "timer": getattr(beacon, "timer", None),
                    "jitter": getattr(beacon, "jitter", None),
                })
        if filter == "sessions" or filter is None:
            for userID, session in sessions_list.items():
                sessions.append({
                    "userID": userID,
                    "address": getattr(session, "address", None),
                    "hostname": getattr(session, "hostname", None),
                    "operating_system": getattr(session, "operating_system", None),
                    "last_beacon": getattr(session, "last_beacon", None),
                    "next_beacon": getattr(session, "next_beacon", None),
                    "timer": getattr(session, "timer", None),
                    "jitter": getattr(session, "jitter", None),
            })
        for userID, session in sessions_list.items():
            sessions.append({
                "userID": userID,
                "address": getattr(session, "address", None),
                "hostname": getattr(session, "hostname", None),
                "operating_system": getattr(session, "operating_system", None),
                "mode": getattr(session, "mode", None),
                "load_modules": getattr(session, "load_modules", None),
            })
        return {"beacons": beacons, "sessions": sessions}

    def _register_routes(self):
        @self._app.post("/api/login")
        def login():  # noqa
            try:
                data = request.get_json(force=True)
            except Exception:
                return jsonify({"error": "Invalid JSON"}), 400
            username = (data.get("username") or "").strip().lower()
            password = data.get("password") or ""
            if not username or not password:
                return jsonify({"error": "Missing credentials"}), 400
            if self.authenticate_user(username, password):
                with self._tokens_lock:
                    token_info = self._issue_token(username)
                multiplayer_connections[username] = HTTPClientSession(
                    username=username,
                    token=token_info["token"],
                    address=(request.remote_addr or "0.0.0.0", 0),
                )
                user_obj = getattr(self, "users", {}).get(username) if hasattr(self, "users") else None
                if user_obj:
                    user_obj.auth_token = token_info["token"]
                    user_obj.auth_token_expiry = token_info["expires"]
                cprint(f"User {username} authenticated via HTTP from {request.remote_addr}. Token issued/rotated (expires {token_info['expires']}).", fg="green")
                logger.info(f"HTTP multiplayer login success for {username}")
                return jsonify({"token": token_info["token"], "expires": token_info["expires"], "user": username})
            else:
                logger.warning(f"Authentication failed for user {username}")
                return jsonify({"error": "Authentication failed"}), 401

        @self._app.post("/api/logout")
        def logout():  # noqa
            token = self._get_token()
            if not token:
                return jsonify({"error": "Invalid token"}), 401
            with self._tokens_lock:
                username = self._token_index.pop(token, None)
                if not username:
                    return jsonify({"error": "Invalid token"}), 401
                self._user_tokens.pop(username, None)
            multiplayer_connections.pop(username, None)
            # Clear token on user object if exists
            user_obj = getattr(self, "users", {}).get(username) if hasattr(self, "users") else None
            if user_obj:
                user_obj.auth_token = None
                user_obj.auth_token_expiry = None
            logger.info(f"User {username} logged out")
            return jsonify({"status": "ok"})

        @self._app.get("/api/status")
        def status():  # noqa
            username = self._require_auth()
            if not username:
                return jsonify({"error": "Unauthorized"}), 401
            # Provide token expiry info (remaining seconds)
            with self._tokens_lock:
                record = self._user_tokens.get(username)
                expires_iso = None
                remaining = None
                if record:
                    expires_dt = record.get("expires")
                    if isinstance(expires_dt, datetime):
                        expires_iso = expires_dt.isoformat()
                        remaining = int((expires_dt - datetime.now(timezone.utc)).total_seconds())
            return jsonify({"user": username, "authenticated": True, "expires": expires_iso, "expires_in": remaining})

        @self._app.get("/api/connections")
        def connections():  # noqa
            username = self._require_auth()
            connections_filter = request.args.get("filter")
            if not connections_filter:
                connections_filter = None  
            else:
                if connections_filter not in ["beacons", "sessions"]:
                    return jsonify({"error": "Invalid filter"}), 400
            if not username:
                return jsonify({"error": "Unauthorized"}), 401
            return jsonify(self._get_active_connections(connections_filter))

        @self._app.get("/api/commands")
        def commands():  # noqa
            username = self._require_auth()
            if not username:
                return jsonify({"error": "Unauthorized"}), 401
            uuid = request.args.get("uuid")
            if not uuid:
                return jsonify({"error": "Missing uuid"}), 400
            return jsonify({"response": self._available_commands(uuid)})

        @self._app.get("/ping")
        def ping():  # noqa
            return jsonify({"pong": True})

    # ------ Public API ------
    def start(self):
        """Start the HTTPS Flask server in a background thread."""
        cert_dir = os.path.expanduser(self.config['server']['TLSCertificateDir'])
        tls_key = os.path.join(cert_dir, self.config['server']['TLSkey'])
        tls_cert = os.path.join(cert_dir, self.config['server']['TLSCertificate'])
        if not (os.path.isfile(tls_key) and os.path.isfile(tls_cert)):
            logger.warning("TLS key/cert not found; starting without TLS (development mode)")
            ssl_context = None
        else:
            ssl_context = (tls_cert, tls_key)
        host, port = self.address

        def _run():
            logger.info(f"HTTP Multiplayer server listening on {host}:{port}")
            try:
                # threaded=True to allow multiple clients
                self._app.run(host=host, port=port, ssl_context=ssl_context, threaded=True, use_reloader=False)
            except Exception as e:
                logger.critical(f"Multiplayer HTTP server failed: {e}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return

    # Backwards compatibility: previous code expected accept_connection loop; noop now
    def accept_connection(self):  # pragma: no cover - maintained for interface compatibility
        logger.debug("accept_connection called on HTTP implementation; no-op")
            