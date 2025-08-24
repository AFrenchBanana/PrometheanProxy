"""
Unified console coloring utilities for the server.

- Provides a single place to manage colors and styles.
- Falls back to plain text when stdout is not a TTY.
- Avoids importing colorama everywhere.

Usage examples:
    from Modules.utils.console import cprint, success, error, warn, info, colorize
    success("Operation completed")
    cprint("Important", fg="black", bg="yellow", bold=True)
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
) -> str:
    """Return colored text if supported; otherwise the original text.

    fg: one of {"black","red","green","yellow","blue","magenta","cyan","white"}
    bg: same set, applies background
    bold: apply bright/bold style
    """
    if not (_HAS_COLOR and _is_tty()):
        return text

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

    return f"{style}{bg_map.get(bg)}{fg_map.get(fg)}{text}"


def cprint(text: str, *, fg: Optional[str] = None, bg: Optional[str] = None, bold: bool = False) -> None:
    print(colorize(text, fg=fg, bg=bg, bold=bold))


# Convenience helpers with a consistent palette
def success(text: str) -> None:
    cprint(text, fg="green")


def error(text: str) -> None:
    cprint(text, fg="red")


def warn(text: str) -> None:
    cprint(text, fg="yellow")


def info(text: str) -> None:
    cprint(text, fg="cyan")


def highlight(text: str) -> None:
    cprint(text, fg="black", bg="yellow", bold=True)


def banner(text: str) -> None:
    """Use for ASCII art banners."""
    cprint(text, fg="cyan")
