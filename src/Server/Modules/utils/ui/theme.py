"""
UI Theme Module - Color and Style Configuration

Defines the visual theme for the PrometheanProxy terminal interface.
"""

from rich.theme import Theme

# Custom theme for modern look
PROMETHEAN_THEME = Theme(
    {
        "info": "bright_blue",
        "success": "bright_green",
        "warning": "bright_yellow",
        "error": "bright_red",
        "highlight": "bright_magenta",
        "muted": "dim white",
        "beacon": "bright_cyan",
        "session": "bright_green",
        "command": "bright_yellow",
        "user": "bright_magenta",
        "config": "bright_cyan",
        "database": "bright_blue",
    }
)

# Event type styling configuration
# Format: (icon, color, prefix_label)
EVENT_STYLES = {
    "session": ("●", "bright_green", "SESSION"),
    "session_new": ("◉", "bright_green", "NEW SESSION"),
    "beacon": ("◆", "bright_cyan", "BEACON"),
    "beacon_new": ("◇", "bright_cyan", "NEW BEACON"),
    "command": ("▶", "bright_yellow", "COMMAND"),
    "command_sent": ("↑", "yellow", "SENT"),
    "command_output": ("↓", "bright_blue", "OUTPUT"),
    "command_error": ("✖", "bright_red", "ERROR"),
    "download": ("↓", "bright_blue", "DOWNLOAD"),
    "upload": ("↑", "bright_magenta", "UPLOAD"),
    "disconnect": ("○", "bright_red", "DISCONN"),
    "warning": ("!", "yellow", "WARNING"),
    "error": ("✖", "red", "ERROR"),
    "success": ("✔", "green", "SUCCESS"),
    "info": ("→", "bright_blue", "INFO"),
    "module": ("◈", "bright_magenta", "MODULE"),
    "config": ("⚙", "white", "CONFIG"),
    "user": ("◈", "bright_magenta", "USER"),
}

# Table style configurations
TABLE_STYLES = {
    "sessions": {
        "title_color": "bright_green",
        "border_color": "bright_green",
        "header_bg": "dark_green",
        "icon": "●",
    },
    "beacons": {
        "title_color": "bright_cyan",
        "border_color": "bright_cyan",
        "header_bg": "dark_cyan",
        "icon": "◆",
    },
    "users": {
        "title_color": "bright_magenta",
        "border_color": "bright_magenta",
        "header_bg": "purple4",
        "icon": "◈",
    },
    "config": {
        "title_color": "bright_cyan",
        "border_color": "bright_cyan",
        "header_bg": "dark_cyan",
        "icon": "⚙",
    },
    "menu": {
        "title_color": "bright_magenta",
        "border_color": "bright_magenta",
        "header_bg": "purple4",
        "icon": "◈",
    },
    "help": {
        "title_color": "bright_magenta",
        "border_color": "bright_magenta",
        "header_bg": "purple4",
        "icon": "?",
    },
    "history": {
        "title_color": "bright_yellow",
        "border_color": "bright_yellow",
        "header_bg": "dark_goldenrod",
        "icon": "▶",
    },
    "status": {
        "title_color": "bright_magenta",
        "border_color": "bright_magenta",
        "header_bg": "purple4",
        "icon": "◈",
    },
    "database": {
        "title_color": "bright_cyan",
        "border_color": "bright_cyan",
        "header_bg": "dark_cyan",
        "icon": "◈",
    },
    "multiplayer": {
        "title_color": "bright_magenta",
        "border_color": "bright_magenta",
        "header_bg": "purple4",
        "icon": "◈",
    },
}

# Status indicator styles
STATUS_INDICATORS = {
    "active": ("[bright_green]●[/]", "Active"),
    "inactive": ("[dim]○[/]", "Inactive"),
    "pending": ("[bright_yellow]◐[/]", "Pending"),
    "error": ("[bright_red]✖[/]", "Error"),
    "success": ("[bright_green]✔[/]", "Success"),
    "warning": ("[bright_yellow]![/]", "Warning"),
    "loading": ("[bright_cyan]◐[/]", "Loading"),
    "offline": ("[dim]○[/]", "Offline"),
    "online": ("[bright_green]●[/]", "Online"),
    "remote": ("[bright_cyan]◐[/]", "Remote"),
}
