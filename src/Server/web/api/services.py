"""
PrometheanProxy API Client Service

This module provides a clean interface to interact with the PrometheanProxy
multiplayer server API. It handles authentication, connection management,
command execution, and real-time event streaming.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PrometheanAPIException(Exception):
    """Base exception for PrometheanProxy API errors."""

    pass


class AuthenticationError(PrometheanAPIException):
    """Raised when authentication fails."""

    pass


class ConnectionError(PrometheanAPIException):
    """Raised when connection to the API fails."""

    pass


class PrometheanAPIClient:
    """
    Client for interacting with the PrometheanProxy multiplayer server API.

    This client handles:
    - User authentication and token management
    - Connection listing and details
    - Command execution
    - Automatic token refresh
    - Session management
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout: int = 30,
    ):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the PrometheanProxy API (default from settings)
            verify_ssl: Whether to verify SSL certificates (default from settings)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or settings.PROMETHEAN_API_URL).rstrip("/")
        self.verify_ssl = (
            verify_ssl if verify_ssl is not None else settings.PROMETHEAN_API_VERIFY_SSL
        )
        self.timeout = timeout
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.username: Optional[str] = None

        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Suppress SSL warnings if verification is disabled
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: JSON data for POST requests
            params: Query parameters
            require_auth: Whether authentication is required

        Returns:
            Response JSON data

        Raises:
            AuthenticationError: If authentication is required but not available
            ConnectionError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {}

        # Add authentication if required
        if require_auth:
            if not self.token:
                raise AuthenticationError("Not authenticated")

            # Check if token is expired
            if self.token_expiry and datetime.now(timezone.utc) >= self.token_expiry:
                raise AuthenticationError("Token expired")

            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            # Handle authentication errors
            if response.status_code == 401:
                self.token = None
                self.token_expiry = None
                raise AuthenticationError("Authentication failed or token expired")

            # Raise for other HTTP errors
            response.raise_for_status()

            # Return JSON response
            return response.json()

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error connecting to {url}: {e}")
            raise ConnectionError(f"SSL error: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {url}: {e}")
            raise ConnectionError(f"Connection error: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to {url}: {e}")
            raise ConnectionError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to {url}: {e}")
            raise ConnectionError(f"Request error: {e}")

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with the PrometheanProxy API.

        Args:
            username: Username for authentication
            password: Password for authentication

        Returns:
            Authentication response with token info

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            response = self._make_request(
                method="POST",
                endpoint="/api/login",
                data={"username": username, "password": password},
                require_auth=False,
            )

            self.token = response.get("token")
            self.username = username

            # Parse token expiry
            expires_str = response.get("expires")
            if expires_str:
                try:
                    self.token_expiry = datetime.fromisoformat(
                        expires_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    # Default to 1 hour if parsing fails
                    self.token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            else:
                self.token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

            logger.info(f"Successfully authenticated as {username}")
            return response

        except ConnectionError as e:
            raise AuthenticationError(f"Failed to connect: {e}")
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise AuthenticationError(f"Login failed: {e}")

    def logout(self) -> bool:
        """
        Logout and invalidate the current token.

        Returns:
            True if logout was successful

        Raises:
            ConnectionError: If the request fails
        """
        try:
            self._make_request(method="POST", endpoint="/api/logout")
            self.token = None
            self.token_expiry = None
            self.username = None
            logger.info("Successfully logged out")
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Clear local state even if API call fails
            self.token = None
            self.token_expiry = None
            self.username = None
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get current authentication status.

        Returns:
            Status information including user and token expiry

        Raises:
            AuthenticationError: If not authenticated
            ConnectionError: If the request fails
        """
        return self._make_request(method="GET", endpoint="/api/status")

    def is_authenticated(self) -> bool:
        """
        Check if the client is currently authenticated.

        Returns:
            True if authenticated and token is not expired
        """
        if not self.token:
            return False

        if self.token_expiry and datetime.now(timezone.utc) >= self.token_expiry:
            return False

        return True

    def get_connections(
        self, filter_type: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get list of active connections (beacons and/or sessions).

        Args:
            filter_type: Optional filter - "beacons" or "sessions"

        Returns:
            Dictionary with 'beacons' and/or 'sessions' lists

        Raises:
            AuthenticationError: If not authenticated
            ConnectionError: If the request fails
        """
        params = {}
        if filter_type:
            params["filter"] = filter_type

        return self._make_request(
            method="GET", endpoint="/api/connections", params=params
        )

    def get_connection_details(
        self, uuid: str, include_commands: bool = False
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific connection.

        Args:
            uuid: UUID of the connection
            include_commands: Whether to include command history

        Returns:
            Connection details and optionally command history

        Raises:
            AuthenticationError: If not authenticated
            ConnectionError: If the request fails
        """
        params = {"uuid": uuid}
        if include_commands:
            params["commands"] = ""

        return self._make_request(
            method="GET", endpoint="/api/connections/details", params=params
        )

    def get_available_commands(self, uuid: str) -> Dict[str, Any]:
        """
        Get list of available commands for a specific implant/session.

        Args:
            uuid: UUID of the implant or session

        Returns:
            Available commands

        Raises:
            AuthenticationError: If not authenticated
            ConnectionError: If the request fails
        """
        return self._make_request(
            method="GET", endpoint="/api/commands", params={"uuid": uuid}
        )

    def execute_command(
        self, uuid: str, command: str, data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a command on a specific implant/session.

        Args:
            uuid: UUID of the target implant or session
            command: Command to execute
            data: Optional command data/arguments

        Returns:
            Command execution status

        Raises:
            AuthenticationError: If not authenticated
            ConnectionError: If the request fails
        """
        payload = {"uuid": uuid, "command": command}
        if data is not None:
            payload["data"] = data

        return self._make_request(method="POST", endpoint="/api/commands", data=payload)

    def ping(self) -> bool:
        """
        Check if the API server is reachable.

        Returns:
            True if server is reachable

        Raises:
            ConnectionError: If the request fails
        """
        try:
            response = self._make_request(
                method="GET", endpoint="/ping", require_auth=False
            )
            return response.get("pong", False)
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            raise ConnectionError(f"Server unreachable: {e}")

    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.close()


# Singleton instance for shared use across the application
_api_client: Optional[PrometheanAPIClient] = None


def get_api_client() -> PrometheanAPIClient:
    """
    Get or create the shared API client instance.

    Returns:
        Shared PrometheanAPIClient instance
    """
    global _api_client
    if _api_client is None:
        _api_client = PrometheanAPIClient()
    return _api_client


def reset_api_client():
    """Reset the shared API client instance."""
    global _api_client
    if _api_client:
        _api_client.close()
    _api_client = None
