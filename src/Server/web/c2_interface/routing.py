"""
WebSocket URL Routing for C2 Interface

Defines WebSocket URL patterns for real-time event streaming and monitoring.
"""

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    # Global events stream
    path("ws/events/", consumers.EventsConsumer.as_asgi(), name="ws_events"),
    # Beacon-specific monitoring
    path(
        "ws/beacons/<str:uuid>/", consumers.BeaconConsumer.as_asgi(), name="ws_beacon"
    ),
    # Session-specific monitoring
    path(
        "ws/sessions/<str:uuid>/",
        consumers.SessionConsumer.as_asgi(),
        name="ws_session",
    ),
    # All connections monitoring
    path(
        "ws/connections/",
        consumers.ConnectionsConsumer.as_asgi(),
        name="ws_connections",
    ),
    # Command monitoring and execution
    path("ws/commands/", consumers.CommandConsumer.as_asgi(), name="ws_commands"),
]
