"""
Django REST Framework Views for PrometheanProxy API

This module provides API endpoints that interact with the PrometheanProxy
multiplayer server, handling authentication, connection management, and
command execution through a clean RESTful interface.
"""

import logging
from datetime import datetime

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AvailableCommandsSerializer,
    CommandExecutionResponseSerializer,
    ConnectionDetailsResponseSerializer,
    ConnectionsListSerializer,
    ErrorResponseSerializer,
    ExecuteCommandSerializer,
    LoginSerializer,
    PingResponseSerializer,
    StatusSerializer,
    SuccessResponseSerializer,
    TokenResponseSerializer,
)
from .services import (
    AuthenticationError,
    ConnectionError,
    PrometheanAPIException,
    get_api_client,
)

logger = logging.getLogger(__name__)


def extract_and_apply_token(request, client):
    """
    Extract token from Authorization header and temporarily apply it to the client.

    Args:
        request: Django request object
        client: PrometheanAPIClient instance

    Returns:
        tuple: (token, original_token) for restoration, or (None, None) if no token
    """
    auth_header = request.headers.get("Authorization", "")
    token = None

    if auth_header.startswith("Token "):
        token = auth_header[6:]
    elif auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if token:
        original_token = client.token
        client.token = token
        return token, original_token

    return None, None


@method_decorator(csrf_exempt, name="dispatch")
class HealthCheckView(APIView):
    """
    Health check endpoint to verify API is running.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Check API health."""
        return Response(
            {"pong": True, "timestamp": datetime.utcnow()}, status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name="dispatch")
class PrometheusHealthView(APIView):
    """
    Check connectivity to the PrometheanProxy backend server.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Ping the PrometheanProxy backend server."""
        try:
            client = get_api_client()
            result = client.ping()
            return Response(
                {
                    "pong": result,
                    "timestamp": datetime.utcnow(),
                    "backend": "connected",
                },
                status=status.HTTP_200_OK,
            )
        except ConnectionError as e:
            logger.error(f"Backend health check failed: {e}")
            return Response(
                {"error": "Backend unreachable", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    Authenticate with the PrometheanProxy backend and receive an auth token.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Authenticate user and return backend token.

        This endpoint proxies authentication to the PrometheanProxy backend
        and returns the backend token, which should be used for subsequent requests.
        """
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        try:
            client = get_api_client()
            response = client.login(username, password)

            logger.info(f"User {username} authenticated successfully")
            return Response(response, status=status.HTTP_200_OK)

        except AuthenticationError as e:
            logger.warning(f"Authentication failed for {username}: {e}")
            return Response(
                {"error": "Authentication failed", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error during login: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            return Response(
                {"error": "Internal server error", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """
    Logout and invalidate the current authentication token.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Logout user and invalidate token."""
        try:
            client = get_api_client()
            client.logout()

            return Response(
                {"status": "ok", "message": "Logged out successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {"error": "Logout failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class StatusView(APIView):
    """
    Get current authentication status.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Get authentication status."""
        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"authenticated": False, "error": "No token provided"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            try:
                response = client.get_status()
                return Response(
                    {"authenticated": True, "status": response},
                    status=status.HTTP_200_OK,
                )
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {
                    "authenticated": False,
                    "error": "Not authenticated",
                    "detail": str(e),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return Response(
                {
                    "authenticated": False,
                    "error": "Status check failed",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class ConnectionsListView(APIView):
    """
    List all active connections (beacons and sessions).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get active connections.

        Query parameters:
        - filter: 'beacons' or 'sessions' to filter results
        """
        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"error": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                filter_type = request.query_params.get("filter")
                if filter_type and filter_type not in ["beacons", "sessions"]:
                    return Response(
                        {"error": "Invalid filter parameter"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                connections = client.get_connections(filter_type)
                return Response(connections, status=status.HTTP_200_OK)
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {"error": "Authentication required", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error fetching connections: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Error fetching connections: {e}")
            return Response(
                {"error": "Failed to fetch connections", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class BeaconsOnlyListView(APIView):
    """
    List only active beacons (filters out sessions).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get active beacons only.
        """
        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"error": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                connections = client.get_connections("beacons")
                # Return just the beacons list
                beacons = connections.get("beacons", [])
                return Response({"beacons": beacons}, status=status.HTTP_200_OK)
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {"error": "Authentication required", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error fetching beacons: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Error fetching beacons: {e}")
            return Response(
                {"error": "Failed to fetch beacons", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class ConnectionDetailView(APIView):
    """
    Get detailed information about a specific connection.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get connection details.

        Query parameters:
        - uuid: Connection UUID (required)
        - commands: Include command history if present
        """
        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"error": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                uuid = request.query_params.get("uuid")
                if not uuid:
                    return Response(
                        {"error": "UUID parameter required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                include_commands = "commands" in request.query_params
                details = client.get_connection_details(uuid, include_commands)

                if not details.get("connection"):
                    return Response(
                        {"error": "Connection not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                return Response(details, status=status.HTTP_200_OK)
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {"error": "Authentication required", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error fetching details: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Error fetching connection details: {e}")
            return Response(
                {"error": "Failed to fetch connection details", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class AvailableCommandsView(APIView):
    """
    Get list of available commands for a specific connection.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get available commands for a connection.

        Query parameters:
        - uuid: Connection UUID (required)
        """
        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"error": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                uuid = request.query_params.get("uuid")
                if not uuid:
                    return Response(
                        {"error": "UUID parameter required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                commands = client.get_available_commands(uuid)

                # Check if response indicates error
                if isinstance(
                    commands.get("response"), dict
                ) and "error" in commands.get("response", {}):
                    return Response(
                        commands.get("response"), status=status.HTTP_404_NOT_FOUND
                    )

                return Response(commands, status=status.HTTP_200_OK)
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {"error": "Authentication required", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error fetching commands: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(f"Error fetching available commands: {e}")
            return Response(
                {"error": "Failed to fetch available commands", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class ExecuteCommandView(APIView):
    """
    Execute a command on a specific connection.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Execute a command.

        Request body:
        - uuid: Target connection UUID
        - command: Command to execute
        - data: Optional command arguments
        """
        serializer = ExecuteCommandSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_api_client()
            token, original_token = extract_and_apply_token(request, client)

            if not token:
                return Response(
                    {"error": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                uuid = serializer.validated_data["uuid"]
                command = serializer.validated_data["command"]
                data = serializer.validated_data.get("data")

                result = client.execute_command(uuid, command, data)

                logger.info(f"Command '{command}' executed on {uuid}")
                return Response(result, status=status.HTTP_200_OK)
            finally:
                # Restore original token
                client.token = original_token

        except AuthenticationError as e:
            return Response(
                {"error": "Authentication required", "detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except ConnectionError as e:
            logger.error(f"Connection error executing command: {e}")
            return Response(
                {"error": "Backend connection failed", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PrometheanAPIException as e:
            logger.error(f"API error executing command: {e}")
            return Response(
                {"error": "Command execution failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return Response(
                {"error": "Failed to execute command", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Function-based view for quick testing
@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    """
    Get API information and available endpoints.
    """
    return Response(
        {
            "name": "PrometheanProxy Web API",
            "version": "1.0.0",
            "description": "RESTful API for interacting with PrometheanProxy C2 server",
            "endpoints": {
                "health": "/api/health/",
                "backend_health": "/api/health/backend/",
                "login": "/api/auth/login/",
                "logout": "/api/auth/logout/",
                "status": "/api/auth/status/",
                "connections": "/api/connections/",
                "connection_details": "/api/connections/details/",
                "commands": "/api/commands/",
                "execute_command": "/api/commands/execute/",
            },
            "websocket": {
                "events": "ws://<host>/ws/events/",
                "beacons": "ws://<host>/ws/beacons/<uuid>/",
            },
        },
        status=status.HTTP_200_OK,
    )
