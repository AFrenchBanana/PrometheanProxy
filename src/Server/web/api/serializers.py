"""
Django REST Framework Serializers for PrometheanProxy API

This module defines serializers for all API endpoints, handling data
validation and serialization for connections, commands, and authentication.
"""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Serializer for user login requests."""

    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        max_length=128, required=True, write_only=True, style={"input_type": "password"}
    )


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for authentication token response."""

    token = serializers.CharField(read_only=True)
    expires = serializers.DateTimeField(read_only=True, required=False)
    expires_in = serializers.IntegerField(read_only=True, required=False)
    user = serializers.CharField(read_only=True)


class StatusSerializer(serializers.Serializer):
    """Serializer for authentication status response."""

    user = serializers.CharField(read_only=True)
    authenticated = serializers.BooleanField(read_only=True)
    expires = serializers.DateTimeField(read_only=True, required=False, allow_null=True)
    expires_in = serializers.IntegerField(
        read_only=True, required=False, allow_null=True
    )


class BeaconSerializer(serializers.Serializer):
    """Serializer for beacon connection information."""

    userID = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True, allow_null=True)
    address = serializers.CharField(read_only=True, allow_null=True)
    hostname = serializers.CharField(read_only=True, allow_null=True)
    operating_system = serializers.CharField(read_only=True, allow_null=True)
    last_beacon = serializers.CharField(read_only=True, allow_null=True)
    next_beacon = serializers.CharField(read_only=True, allow_null=True)
    timer = serializers.IntegerField(read_only=True, allow_null=True)
    jitter = serializers.IntegerField(read_only=True, allow_null=True)


class SessionSerializer(serializers.Serializer):
    """Serializer for session connection information."""

    userID = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True, allow_null=True)
    address = serializers.CharField(read_only=True, allow_null=True)
    hostname = serializers.CharField(read_only=True, allow_null=True)
    operating_system = serializers.CharField(read_only=True, allow_null=True)
    mode = serializers.CharField(read_only=True, allow_null=True)
    load_modules = serializers.ListField(
        child=serializers.CharField(), read_only=True, allow_null=True
    )


class ConnectionsListSerializer(serializers.Serializer):
    """Serializer for connections list response."""

    beacons = BeaconSerializer(many=True, read_only=True, required=False)
    sessions = SessionSerializer(many=True, read_only=True, required=False)


class ConnectionDetailSerializer(serializers.Serializer):
    """Serializer for detailed connection information."""

    type = serializers.ChoiceField(choices=["beacon", "session"], read_only=True)
    userID = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True, allow_null=True)
    hostname = serializers.CharField(read_only=True, allow_null=True)
    operating_system = serializers.CharField(read_only=True, allow_null=True)

    # Beacon-specific fields
    last_beacon = serializers.CharField(read_only=True, required=False, allow_null=True)
    next_beacon = serializers.CharField(read_only=True, required=False, allow_null=True)
    timer = serializers.IntegerField(read_only=True, required=False, allow_null=True)
    jitter = serializers.IntegerField(read_only=True, required=False, allow_null=True)

    # Session-specific fields
    mode = serializers.CharField(read_only=True, required=False, allow_null=True)
    load_modules = serializers.ListField(
        child=serializers.CharField(), read_only=True, required=False, allow_null=True
    )


class CommandHistorySerializer(serializers.Serializer):
    """Serializer for command history entry."""

    command_uuid = serializers.CharField(read_only=True, allow_null=True)
    command = serializers.CharField(read_only=True, allow_null=True)
    data = serializers.CharField(read_only=True, allow_null=True)
    executed = serializers.BooleanField(read_only=True, default=False)
    output = serializers.CharField(read_only=True, allow_null=True)


class ConnectionDetailsResponseSerializer(serializers.Serializer):
    """Serializer for connection details with optional command history."""

    connection = ConnectionDetailSerializer(read_only=True, required=False)
    commands = CommandHistorySerializer(many=True, read_only=True, required=False)


class AvailableCommandsSerializer(serializers.Serializer):
    """Serializer for available commands response."""

    response = serializers.ListField(child=serializers.CharField(), read_only=True)


class ExecuteCommandSerializer(serializers.Serializer):
    """Serializer for command execution request."""

    uuid = serializers.CharField(required=True, help_text="Target implant/session UUID")
    command = serializers.CharField(required=True, help_text="Command to execute")
    data = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional command data/arguments",
    )


class CommandExecutionResponseSerializer(serializers.Serializer):
    """Serializer for command execution response."""

    status = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    command = serializers.CharField(read_only=True)


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    error = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True, required=False)


class SuccessResponseSerializer(serializers.Serializer):
    """Serializer for generic success responses."""

    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True, required=False)


class PingResponseSerializer(serializers.Serializer):
    """Serializer for ping/health check response."""

    pong = serializers.BooleanField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True, required=False)


class WebSocketMessageSerializer(serializers.Serializer):
    """Serializer for WebSocket messages."""

    type = serializers.CharField(required=True)
    data = serializers.JSONField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField(required=False)


class BeaconUpdateSerializer(serializers.Serializer):
    """Serializer for beacon update events."""

    event = serializers.ChoiceField(
        choices=["new_beacon", "beacon_checkin", "beacon_disconnected"],
        required=True,
    )
    uuid = serializers.CharField(required=True)
    beacon = BeaconSerializer(required=False)
    timestamp = serializers.DateTimeField(required=False)


class CommandUpdateSerializer(serializers.Serializer):
    """Serializer for command execution update events."""

    event = serializers.ChoiceField(
        choices=["command_issued", "command_executed", "command_failed"],
        required=True,
    )
    uuid = serializers.CharField(required=True)
    command_uuid = serializers.CharField(required=False)
    command = serializers.CharField(required=False)
    output = serializers.CharField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField(required=False)
