"""
C2 Interface URL Configuration

Defines URL patterns for the PrometheanProxy web interface,
including dashboard, beacons, sessions, and command views.
"""

from django.urls import path

from . import views

app_name = "c2_interface"

urlpatterns = [
    # Authentication
    path("login/", views.LoginView.as_view(), name="login"),
    # Main dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Beacons
    path("beacons/", views.BeaconsListView.as_view(), name="beacons_list"),
    path("beacons/<str:uuid>/", views.BeaconDetailView.as_view(), name="beacon_detail"),
    # Sessions
    path("sessions/", views.SessionsListView.as_view(), name="sessions_list"),
    path(
        "sessions/<str:uuid>/", views.SessionDetailView.as_view(), name="session_detail"
    ),
    # Commands
    path("commands/", views.CommandsView.as_view(), name="commands"),
    # Settings and system
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("logs/", views.LogsView.as_view(), name="logs"),
    path("about/", views.AboutView.as_view(), name="about"),
]
