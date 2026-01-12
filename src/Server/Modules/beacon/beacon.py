# ============================================================================
# Beacon Module - Compatibility Wrapper
# ============================================================================
# This module provides backward compatibility by re-exporting the Beacon
# class and related functions from their new modular locations.
#
# The Beacon functionality has been split into smaller, more manageable
# modules:
#   - core.py: Main Beacon class
#   - command.py: beacon_command class for queued commands
#   - registry.py: Global beacon/command management functions
#   - modules.py: Module loading functionality (ModulesMixin)
#   - history.py: Command history and configuration (HistoryMixin)
#   - connection.py: Connection management methods (ConnectionMixin)
#
# For new code, prefer importing directly from the submodules:
#   from Modules.beacon.core import Beacon
#   from Modules.beacon.registry import add_beacon_list, remove_beacon_list
# ============================================================================

# Re-export global objects that were previously accessible via this module
from ..global_objects import command_list

# Re-export beacon_command class
from .command import beacon_command

# Re-export mixins for direct access if needed
from .connection import ConnectionMixin

# Re-export main Beacon class
from .core import Beacon
from .history import HistoryMixin
from .modules import ModulesMixin

# Re-export registry functions for backward compatibility
from .registry import (
    add_beacon_command_list,
    add_beacon_list,
    remove_beacon_list,
)

__all__ = [
    # Main classes
    "Beacon",
    "beacon_command",
    # Global objects
    "command_list",
    # Registry functions
    "add_beacon_list",
    "add_beacon_command_list",
    "remove_beacon_list",
    # Mixins
    "HistoryMixin",
    "ModulesMixin",
    "ConnectionMixin",
]
