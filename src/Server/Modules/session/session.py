# ============================================================================
# Session Module - Compatibility Wrapper
# ============================================================================
# This module provides backward compatibility by re-exporting the Session
# class and related functions from their new modular locations.
#
# The Session functionality has been split into smaller, more manageable
# modules:
#   - core.py: Main Session class
#   - registry.py: Session management functions (add/remove)
#   - commands/: Command handler modules
#
# For new code, prefer importing directly from the submodules:
#   from Modules.session.core import Session
#   from Modules.session.registry import add_connection_list, remove_connection_list
# ============================================================================

# Re-export main Session class
from .core import Session

# Re-export registry functions for backward compatibility
from .registry import add_connection_list, remove_connection_list

__all__ = [
    # Main class
    "Session",
    # Registry functions
    "add_connection_list",
    "remove_connection_list",
]
