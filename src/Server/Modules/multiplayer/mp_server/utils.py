"""
Utility functions for the multiplayer HTTP server.
Provides token management and helper functions.
"""

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from Modules.global_objects import logger


@dataclass
class HTTPClientSession:
    """Represents an authenticated HTTP multiplayer client session."""

    username: str
    token: str
    address: tuple
    is_authenticated: bool = True


class TokenManager:
    """
    Manages authentication tokens for multiplayer clients.

    Token Model:
        One active token per user. Re-authentication rotates the token; any previous token
        for that user becomes invalid immediately. Internally we store a username->token map
        plus a reverse index for O(1) token->username lookups.
    """

    def __init__(self, token_ttl_seconds: int = 7 * 24 * 60 * 60):
        """
        Initialize the token manager.

        Args:
            token_ttl_seconds: Token time-to-live in seconds (default: 1 week)
        """
        # Per-user token store: username -> {token: str, expires: datetime}
        self._user_tokens: dict = {}
        # Reverse index for quick token -> username lookup (only currently valid tokens)
        self._token_index: dict = {}
        self._tokens_lock = threading.Lock()
        self._token_ttl = token_ttl_seconds

    def generate_token(self) -> str:
        """Generate a new secure token."""
        return secrets.token_hex(24)

    def issue_token(self, username: str) -> dict:
        """
        Generate and store a new token (rotating any previous) for a user.

        Args:
            username: The username to issue a token for

        Returns:
            dict with token and expiry ISO string
        """
        new_token = self.generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._token_ttl)

        with self._tokens_lock:
            # Rotate existing token if any
            old_record = self._user_tokens.get(username)
            if old_record:
                old_token = old_record.get("token")
                if old_token:
                    self._token_index.pop(old_token, None)

            self._user_tokens[username] = {"token": new_token, "expires": expires_at}
            self._token_index[new_token] = username

        return {"token": new_token, "expires": expires_at.isoformat()}

    def validate_token(self, token: str) -> Optional[str]:
        """
        Validate a token and return the associated username if valid.

        Args:
            token: The token to validate

        Returns:
            The username if token is valid, None otherwise
        """
        if not token:
            return None

        with self._tokens_lock:
            username = self._token_index.get(token)
            if not username:
                return None

            record = self._user_tokens.get(username)
            if not record or record.get("token") != token:
                # Stale mapping; cleanup just in case
                self._token_index.pop(token, None)
                return None

            expires: datetime = record.get("expires")
            if expires and datetime.now(timezone.utc) >= expires:
                # Expired token: remove
                self._token_index.pop(token, None)
                self._user_tokens.pop(username, None)
                logger.info(f"Expired token for user {username} rejected")
                return None

            return username

    def invalidate_token(self, token: str) -> Optional[str]:
        """
        Invalidate a token (logout).

        Args:
            token: The token to invalidate

        Returns:
            The username that was logged out, or None if token was invalid
        """
        with self._tokens_lock:
            username = self._token_index.pop(token, None)
            if not username:
                return None
            self._user_tokens.pop(username, None)

        logger.info(f"User {username} logged out")
        return username

    def get_token_info(self, username: str) -> Optional[dict]:
        """
        Get token expiry information for a user.

        Args:
            username: The username to get token info for

        Returns:
            dict with expires (ISO string) and expires_in (seconds) or None
        """
        with self._tokens_lock:
            record = self._user_tokens.get(username)
            if not record:
                return None

            expires_dt = record.get("expires")
            if not isinstance(expires_dt, datetime):
                return None

            expires_iso = expires_dt.isoformat()
            remaining = int((expires_dt - datetime.now(timezone.utc)).total_seconds())

            return {"expires": expires_iso, "expires_in": remaining}


def get_token_ttl_from_config(config: dict, default: int = 7 * 24 * 60 * 60) -> int:
    """
    Extract token TTL from config, with fallback to default.

    Args:
        config: Configuration dictionary
        default: Default TTL in seconds (1 week)

    Returns:
        Token TTL in seconds
    """
    try:
        ttl_cfg = config.get("multiplayer", {}).get("tokenTTLSeconds")
        return int(ttl_cfg) if ttl_cfg else default
    except (TypeError, ValueError):
        return default
