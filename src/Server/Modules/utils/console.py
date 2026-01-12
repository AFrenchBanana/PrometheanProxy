"""
Unified console coloring utilities for the server.

- Provides a single place to manage colors and styles.
- Falls back to plain text when stdout is not a TTY.
- Enhanced color scheme for better visual distinction.

Usage examples:
    from Modules.utils.console import cprint, success, error, warn, info, colorize
    success("Operation completed")
    cprint("Important", fg="magenta", bg="black", bold=True)
"""

from __future__ import annotations

import sys
from typing import Optional

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    _HAS_COLOR = True
except Exception:  # pragma: no cover - graceful fallback if colorama missing
    colorama = None
    Fore = Back = Style = None  # type: ignore
    _HAS_COLOR = False


def _is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def colorize(
    text: str,
    *,
    fg: Optional[str] = None,
    bg: Optional[str] = None,
    bold: bool = False,
    dim: bool = False,
) -> str:
    """Return colored text if supported; otherwise the original text.

    fg: one of {"black","red","green","yellow","blue","magenta","cyan","white","bright_*"}
    bg: same set, applies background
    bold: apply bright/bold style
    dim: apply dim style
    """
    if not (_HAS_COLOR and _is_tty()):
        return text

    # Extended color map with bright variants
    fg_map = {
        None: "",
        "black": Fore.BLACK,
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
        "bright_black": Fore.LIGHTBLACK_EX,
        "bright_red": Fore.LIGHTRED_EX,
        "bright_green": Fore.LIGHTGREEN_EX,
        "bright_yellow": Fore.LIGHTYELLOW_EX,
        "bright_blue": Fore.LIGHTBLUE_EX,
        "bright_magenta": Fore.LIGHTMAGENTA_EX,
        "bright_cyan": Fore.LIGHTCYAN_EX,
        "bright_white": Fore.LIGHTWHITE_EX,
    }
    bg_map = {
        None: "",
        "black": Back.BLACK,
        "red": Back.RED,
        "green": Back.GREEN,
        "yellow": Back.YELLOW,
        "blue": Back.BLUE,
        "magenta": Back.MAGENTA,
        "cyan": Back.CYAN,
        "white": Back.WHITE,
    }

    style = ""
    if bold:
        style += Style.BRIGHT
    if dim:
        style += Style.DIM

    return f"{style}{bg_map.get(bg)}{fg_map.get(fg)}{text}{Style.RESET_ALL if _HAS_COLOR else ''}"


def cprint(
    text: str,
    *,
    fg: Optional[str] = None,
    bg: Optional[str] = None,
    bold: bool = False,
    dim: bool = False,
) -> None:
    print(colorize(text, fg=fg, bg=bg, bold=bold, dim=dim))


# Enhanced convenience helpers with improved color palette
def success(text: str) -> None:
    """Print success message in bright green with checkmark."""
    cprint(f"✓ {text}", fg="bright_green", bold=True)


def error(text: str) -> None:
    """Print error message in bright red with X mark."""
    cprint(f"✗ {text}", fg="bright_red", bold=True)


def warn(text: str) -> None:
    """Print warning message in bright yellow with warning symbol."""
    cprint(f"⚠ {text}", fg="bright_yellow", bold=True)


def info(text: str) -> None:
    """Print info message in bright cyan with info symbol."""
    cprint(f"ℹ {text}", fg="bright_cyan")


def debug(text: str) -> None:
    """Print debug message in dim white."""
    cprint(f"🔍 {text}", fg="white", dim=True)


def highlight(text: str) -> None:
    """Print highlighted message for important notices."""
    cprint(f" {text} ", fg="black", bg="yellow", bold=True)


def banner(text: str) -> None:
    """Use for ASCII art banners in bright cyan."""
    cprint(text, fg="bright_cyan", bold=True)



def command_output(text: str) -> None:
    """Print command output in bright white."""
    cprint(text, fg="bright_white")



def prompt(text: str) -> None:
    """Print prompt text in bright magenta."""
    cprint(text, fg="bright_magenta", bold=True)



def status(text: str, status_type: str = "info") -> None:
    """
    Print status message with appropriate styling.
    
    Args:
        text: Status message
        status_type: One of 'info', 'success', 'warning', 'error'
    """
    if status_type == "success":
        success(text)
    elif status_type == "error":
        error(text)
    elif status_type == "warning":
        warn(text)
    else:
        info(text)

        info(text)
