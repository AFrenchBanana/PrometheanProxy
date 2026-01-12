# ============================================================================
# Multi Handler Module - Compatibility Wrapper
# ============================================================================
# This module provides backward compatibility by re-exporting the MultiHandler
# class from its new modular location.
#
# The MultiHandler functionality has been split into smaller, more manageable
# modules:
#   - core.py: Main MultiHandler class and command interface
#   - security.py: TLS certificate and HMAC key management
#   - socket_server.py: SSL socket server and connection handling
#   - loader.py: Database loading for persisted implants
#
# For new code, prefer importing directly from the submodules:
#   from Modules.multi_handler.core import MultiHandler
# ============================================================================

# Re-export MultiHandler for backward compatibility
from .core import MultiHandler

# Re-export mixins for direct access if needed
from .loader import LoaderMixin
from .security import SecurityMixin
from .socket_server import SocketServerMixin

__all__ = [
    "MultiHandler",
    "SecurityMixin",
    "SocketServerMixin",
    "LoaderMixin",
]
