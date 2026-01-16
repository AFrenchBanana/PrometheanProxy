"""
C2 Interface Views

Django views for the PrometheanProxy web interface.
Provides dashboard, beacon management, session management, and command execution.
"""

import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class DashboardView(TemplateView):
    """
    Main dashboard view showing overview of all beacons and sessions.
    """

    template_name = "c2_interface/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Dashboard"
        context["active_page"] = "dashboard"
        return context


class BeaconsListView(TemplateView):
    """
    List all active beacons with filtering and search capabilities.
    """

    template_name = "c2_interface/beacons_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Beacons"
        context["active_page"] = "beacons"
        return context


class BeaconDetailView(TemplateView):
    """
    Detailed view of a specific beacon with command execution interface.
    """

    template_name = "c2_interface/beacon_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        beacon_uuid = kwargs.get("uuid")
        context["page_title"] = f"Beacon {beacon_uuid[:8]}..."
        context["active_page"] = "beacons"
        context["beacon_uuid"] = beacon_uuid
        return context


class SessionsListView(TemplateView):
    """
    List all active sessions.
    """

    template_name = "c2_interface/sessions_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Sessions"
        context["active_page"] = "sessions"
        return context


class SessionDetailView(TemplateView):
    """
    Interactive session view with terminal interface.
    """

    template_name = "c2_interface/session_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_uuid = kwargs.get("uuid")
        context["page_title"] = f"Session {session_uuid[:8]}..."
        context["active_page"] = "sessions"
        context["session_uuid"] = session_uuid
        return context


class CommandsView(TemplateView):
    """
    Command history and management view.
    """

    template_name = "c2_interface/commands.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Commands"
        context["active_page"] = "commands"
        return context


class LoginView(TemplateView):
    """
    Login page for authentication with PrometheanProxy backend.
    """

    template_name = "c2_interface/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Login"
        return context


class SettingsView(TemplateView):
    """
    Application settings and configuration.
    """

    template_name = "c2_interface/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Settings"
        context["active_page"] = "settings"
        return context


class LogsView(TemplateView):
    """
    System logs and activity monitoring.
    """

    template_name = "c2_interface/logs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Logs"
        context["active_page"] = "logs"
        return context


class AboutView(TemplateView):
    """
    About page with system information.
    """

    template_name = "c2_interface/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "About"
        return context
