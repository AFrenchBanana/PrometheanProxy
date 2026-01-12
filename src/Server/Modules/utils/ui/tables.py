"""
UI Tables Module - Table Creation Functions

Provides factory functions for creating styled Rich tables
used throughout the PrometheanProxy terminal interface.
"""

from typing import Any, Dict, List, Optional

from rich.box import MINIMAL_DOUBLE_HEAD, ROUNDED
from rich.table import Table

from .theme import TABLE_STYLES


def create_sessions_table(sessions: Dict) -> Table:
    """
    Create a modern styled sessions table.

    Args:
        sessions: Dictionary mapping session IDs to session objects

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["sessions"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Active Sessions[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        row_styles=["", "dim"],
        padding=(0, 1),
        expand=True,
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("UUID", style="bright_blue", max_width=12, no_wrap=True)
    table.add_column("Hostname", style="bright_green")
    table.add_column("IP Address", style="white")
    table.add_column("OS", style="bright_cyan")
    table.add_column("Mode", style="bright_magenta")

    for idx, (session_id, session) in enumerate(sessions.items()):
        uuid_display = session_id[:12] + "..." if len(session_id) > 12 else session_id
        address = (
            session.address[0]
            if isinstance(session.address, tuple)
            else str(session.address)
        )
        table.add_row(
            str(idx),
            uuid_display,
            session.hostname,
            address,
            session.operating_system,
            getattr(session, "mode", "session"),
        )

    return table


def create_beacons_table(beacons: Dict) -> Table:
    """
    Create a modern styled beacons table.

    Args:
        beacons: Dictionary mapping beacon IDs to beacon objects

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["beacons"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Active Beacons[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        row_styles=["", "dim"],
        padding=(0, 1),
        expand=True,
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("UUID", style="bright_blue", max_width=12, no_wrap=True)
    table.add_column("Hostname", style="bright_cyan")
    table.add_column("IP Address", style="white")
    table.add_column("OS", style="bright_magenta")
    table.add_column("Last Seen", style="bright_yellow")
    table.add_column("Next Check-in", style="green")
    table.add_column("Status", style="white")

    for idx, (beacon_id, beacon) in enumerate(beacons.items()):
        # Determine status
        status = "[bright_green]● Active[/]"
        if hasattr(beacon, "loaded_this_instant") and not beacon.loaded_this_instant:
            status = "[bright_yellow]◐ Loaded from DB[/]"

        uuid_display = beacon_id[:12] + "..." if len(beacon_id) > 12 else beacon_id
        last_beacon = (
            str(beacon.last_beacon) if hasattr(beacon, "last_beacon") else "N/A"
        )
        next_beacon = (
            str(beacon.next_beacon) if hasattr(beacon, "next_beacon") else "N/A"
        )

        table.add_row(
            str(idx),
            uuid_display,
            beacon.hostname,
            beacon.address,
            beacon.operating_system,
            last_beacon,
            next_beacon,
            status,
        )

    return table


def create_users_table(users: Dict, current_user_id: Optional[str] = None) -> Table:
    """
    Create a modern styled users table.

    Args:
        users: Dictionary mapping user IDs to user objects
        current_user_id: ID of the currently logged in user

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["users"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Users[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        row_styles=["", "dim"],
        padding=(0, 1),
        expand=True,
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Username", style="bright_cyan")
    table.add_column("Role", style="bright_yellow")
    table.add_column("Status", style="white")

    for idx, (user_id, user) in enumerate(users.items()):
        # Determine role
        role = "[bright_red]Admin[/]" if user.admin else "[white]User[/]"

        # Determine status
        if current_user_id == user_id:
            status = "[bright_green]● Current User[/]"
        elif user.auth_token is not None:
            status = "[bright_cyan]◐ Remote Login[/]"
        else:
            status = "[dim]○ Offline[/]"

        table.add_row(
            str(idx + 1),
            user.username,
            role,
            status,
        )

    return table


def create_status_table(stats: Dict[str, Any]) -> Table:
    """
    Create a compact status overview table.

    Args:
        stats: Dictionary with status metrics

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["status"]
    table = Table(
        box=MINIMAL_DOUBLE_HEAD,
        border_style=style["border_color"],
        header_style=f"bold {style['title_color']}",
        padding=(0, 2),
        expand=False,
    )

    table.add_column("Metric", style="bright_white")
    table.add_column("Value", style="bright_cyan", justify="right")

    session_style = "bright_green" if stats.get("sessions", 0) > 0 else "dim"
    beacon_style = "bright_cyan" if stats.get("beacons", 0) > 0 else "dim"
    total_style = "bright_magenta" if stats.get("total_connections", 0) > 0 else "dim"

    table.add_row("Sessions", f"[{session_style}]{stats.get('sessions', 0)}[/]")
    table.add_row("Beacons", f"[{beacon_style}]{stats.get('beacons', 0)}[/]")
    table.add_row(
        "Total Connections",
        f"[{total_style}]{stats.get('total_connections', 0)}[/]",
    )
    table.add_row(
        "Commands Executed",
        f"[bright_yellow]{stats.get('commands_executed', 0)}[/]",
    )

    uptime = stats.get("uptime", "N/A")
    table.add_row("Uptime", f"[bright_green]{uptime}[/]")

    last_activity = stats.get("last_activity", "None")
    table.add_row("Last Activity", f"[dim]{last_activity}[/]")

    return table


def create_help_table(commands: Dict[str, str]) -> Table:
    """
    Create a modern help table.

    Args:
        commands: Dictionary mapping command names to descriptions

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["help"]
    table = Table(
        title=f"[bold {style['title_color']}]Available Commands[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        padding=(0, 2),
        expand=True,
    )

    table.add_column("Command", style="bright_cyan", width=16)
    table.add_column("Description", style="white")

    for cmd, desc in commands.items():
        table.add_row(cmd, desc)

    return table


def create_command_history_table(commands: List[Dict]) -> Table:
    """
    Create a modern command history table.

    Args:
        commands: List of command dictionaries with command, executed, output keys

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["history"]
    table = Table(
        title=f"[bold {style['title_color']}]Command History[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        row_styles=["", "dim"],
        padding=(0, 1),
        expand=True,
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Command", style="bright_cyan")
    table.add_column("Status", style="white", width=12)
    table.add_column("Output", style="white", max_width=50)

    for idx, cmd in enumerate(commands):
        executed = cmd.get("executed", False)
        status_style = "bright_green" if executed else "bright_yellow"
        status_text = "✔ Complete" if executed else "◐ Pending"

        output = cmd.get("output", "")[:50]
        if len(cmd.get("output", "")) > 50:
            output += "..."

        table.add_row(
            str(idx + 1),
            cmd.get("command", "Unknown"),
            f"[{status_style}]{status_text}[/]",
            output,
        )

    return table


def create_menu_table(title: str, options: Dict[str, str]) -> Table:
    """
    Create a styled menu table.

    Args:
        title: Menu title text
        options: Dictionary mapping option keys to descriptions

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["menu"]
    table = Table(
        title=f"[bold {style['title_color']}]{title}[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        padding=(0, 2),
        expand=False,
    )

    table.add_column("Option", style="bright_cyan", width=8, justify="center")
    table.add_column("Description", style="white")

    for key, desc in options.items():
        table.add_row(f"[bold]{key}[/]", desc)

    return table


def create_config_table(section: str, config_data: Dict) -> Table:
    """
    Create a styled configuration display table.

    Args:
        section: Configuration section name
        config_data: Dictionary of configuration key-value pairs

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["config"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} {section.title()} Configuration[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        row_styles=["", "dim"],
        padding=(0, 2),
        expand=True,
    )

    table.add_column("Setting", style="bright_yellow", width=25)
    table.add_column("Value", style="white")
    table.add_column("Type", style="dim", width=12)

    for key, value in config_data.items():
        value_type = type(value).__name__

        # Style boolean values
        if isinstance(value, bool):
            value_display = (
                "[bright_green]✔ True[/]" if value else "[bright_red]✖ False[/]"
            )
        elif isinstance(value, int):
            value_display = f"[bright_cyan]{value}[/]"
        else:
            value_display = str(value)

        table.add_row(key, value_display, value_type)

    return table


def create_database_config_table(cmd_db_config: Dict, user_db_config: Dict) -> Table:
    """
    Create a database configuration display table.

    Args:
        cmd_db_config: Command database configuration dictionary
        user_db_config: User database configuration dictionary

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["database"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Database Configuration[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        padding=(0, 1),
        expand=True,
    )

    table.add_column("Setting", style="bright_yellow")
    table.add_column("Value", style="white")
    table.add_column("Description", style="dim")

    # Command Database Settings
    table.add_row("[bold bright_magenta]── Command Database ──[/]", "", "")

    file_path = cmd_db_config.get("file", "~/.PrometheanProxy/db/implants.db")
    table.add_row("  file", f"[bright_cyan]{file_path}[/]", "Database file location")

    add_data = cmd_db_config.get("addData", True)
    add_data_style = "bright_green" if add_data else "bright_red"
    table.add_row(
        "  addData", f"[{add_data_style}]{add_data}[/]", "Insert data to database"
    )

    persist_beacons = cmd_db_config.get("persist_beacons", True)
    pb_style = "bright_green" if persist_beacons else "bright_red"
    table.add_row(
        "  persist_beacons",
        f"[{pb_style}]{persist_beacons}[/]",
        "Save beacons across restarts",
    )

    persist_sessions = cmd_db_config.get("persist_sessions", True)
    ps_style = "bright_green" if persist_sessions else "bright_red"
    table.add_row(
        "  persist_sessions",
        f"[{ps_style}]{persist_sessions}[/]",
        "Save sessions across restarts",
    )

    tables_list = cmd_db_config.get("tables", [])
    table.add_row(
        "  tables",
        f"[bright_cyan]{len(tables_list)}[/] custom tables",
        "Defined table schemas",
    )

    # User Database Settings
    table.add_row("[bold bright_magenta]── User Database ──[/]", "", "")

    user_file_path = user_db_config.get("file", "~/.PrometheanProxy/db/user.db")
    table.add_row(
        "  file", f"[bright_cyan]{user_file_path}[/]", "User database file location"
    )

    user_add_data = user_db_config.get("addData", True)
    user_add_data_style = "bright_green" if user_add_data else "bright_red"
    table.add_row(
        "  addData",
        f"[{user_add_data_style}]{user_add_data}[/]",
        "Insert user data to database",
    )

    user_tables_list = user_db_config.get("tables", [])
    table.add_row(
        "  tables",
        f"[bright_cyan]{len(user_tables_list)}[/] custom tables",
        "Defined table schemas",
    )

    return table


def create_tables_list_table(
    command_tables: List[str], user_tables: List[str]
) -> Table:
    """
    Create a table showing all database tables.

    Args:
        command_tables: List of command database table names
        user_tables: List of user database table names

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["database"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Database Tables[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        padding=(0, 1),
        expand=True,
    )

    table.add_column("Database", style="bright_yellow")
    table.add_column("Tables", style="white")

    table.add_row(
        "Command Database",
        ", ".join(command_tables) if command_tables else "[dim]None[/]",
    )
    table.add_row(
        "User Database",
        ", ".join(user_tables) if user_tables else "[dim]None[/]",
    )

    return table


def create_multiplayer_table(connections: Dict) -> Table:
    """
    Create a styled multiplayer connections table.

    Args:
        connections: Dictionary mapping usernames to client objects

    Returns:
        Rich Table object ready for display
    """
    style = TABLE_STYLES["multiplayer"]
    table = Table(
        title=f"[bold {style['title_color']}]{style['icon']} Multiplayer Connections[/]",
        box=ROUNDED,
        border_style=style["border_color"],
        header_style=f"bold bright_white on {style['header_bg']}",
        padding=(0, 1),
        expand=True,
    )

    table.add_column("Username", style="bright_cyan")
    table.add_column("Address", style="white")

    for username, client in connections.items():
        try:
            addr = (
                client.address[0]
                if isinstance(client.address, (list, tuple))
                else str(client.address)
            )
        except Exception:
            addr = "unknown"
        table.add_row(username, addr)

    return table
