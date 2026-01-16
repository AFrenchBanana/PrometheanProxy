"""
Web Server Module for PrometheanProxy
======================================
This module provides Django web interface integration for the PrometheanProxy
MultiHandler system.
"""

from .django_server import start_django_server

__all__ = ["start_django_server"]
