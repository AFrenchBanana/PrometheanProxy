"""
Config Shared Module - Common Imports and Session

Provides shared resources used across all configuration modules.
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

# Shared prompt session for consistent input handling across config modules
_prompt_session = PromptSession()

# Configuration file path
CONFIG_FILE_PATH = "res/config.toml"


def get_prompt_session() -> PromptSession:
    """Get the shared prompt session instance."""
    return _prompt_session


def create_completer(options: list) -> WordCompleter:
    """
    Create a WordCompleter from a list of options.

    Args:
        options: List of completion options

    Returns:
        WordCompleter instance
    """
    return WordCompleter(options, ignore_case=True)
