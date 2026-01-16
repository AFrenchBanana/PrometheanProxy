"""
API URL Configuration

Defines all REST API endpoints for the PrometheanProxy web interface.
These endpoints proxy requests to the backend multiplayer server.
"""

from django.urls import path

from .views import (
    AvailableCommandsView,
    BeaconsOnlyListView,
    ConnectionDetailView,
    ConnectionsListView,
    ExecuteCommandView,
    HealthCheckView,
    LoginView,
    LogoutView,
    PrometheusHealthView,
    StatusView,
    api_info,
)

app_name = "api"

urlpatterns = [
    # API Info
    path("", api_info, name="info"),
    # Health checks
    path("health/", HealthCheckView.as_view(), name="health"),
    path("health/backend/", PrometheusHealthView.as_view(), name="backend_health"),
    # Authentication
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/status/", StatusView.as_view(), name="status"),
    # Connections
    path("connections/", ConnectionsListView.as_view(), name="connections_list"),
    path(
        "connections/details/", ConnectionDetailView.as_view(), name="connection_detail"
    ),
    # Beacons
    path("beacons/", BeaconsOnlyListView.as_view(), name="beacons_list"),
    # Commands
    path("commands/", AvailableCommandsView.as_view(), name="available_commands"),
    path("commands/execute/", ExecuteCommandView.as_view(), name="execute_command"),
]
