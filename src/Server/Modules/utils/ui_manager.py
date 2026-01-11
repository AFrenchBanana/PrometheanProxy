"""
Modern terminal UI manager with pinned header and live updates.

Header: Live-updating stats and activity feed (always visible at top)
Body: Interactive terminal with command output flowing below
"""

from __future__ import annotations

import threading
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, List
from collections import deque

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich import box
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from prompt_toolkit.formatted_text import HTML, ANSI
import io


class UIManager:
    """
    Manages terminal UI with pinned live-updating header.
    
    Header: Stats panel + Activity feed (auto-updates)
    Body: Interactive terminal session
    """
    
    def __init__(self, max_events: int = 25):
        """
        Initialize the UI manager.
        
        Args:
            max_events: Maximum number of events to display in activity feed
        """
        self.console = Console()
        self.events: deque = deque(maxlen=max_events)
        self.lock = threading.Lock()
        self.active = False
        self.update_thread: Optional[threading.Thread] = None
        self.should_stop = False
        self.header_height = 14  # Fixed height for the header area
        
        # Statistics
        self.stats = {
            "sessions": 0,
            "beacons": 0,
            "total_connections": 0,
            "last_activity": "None",
            "server_uptime": datetime.now()
        }
        
    def add_event(self, event_type: str, message: str, details: Optional[Dict] = None):
        """
        Add a new event to the live feed.
        
        Args:
            event_type: Type of event (session, beacon, command, etc.)
            message: Event message to display
            details: Optional additional details
        """
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Enhanced color coding and icons based on event type
            if event_type == "session":
                icon = "🔗"
                color = "bright_green"
                prefix = "SESSION"
            elif event_type == "beacon":
                icon = "📡"
                color = "bright_cyan"
                prefix = "BEACON"
            elif event_type == "command":
                icon = "⚡"
                color = "bright_yellow"
                prefix = "CMD"
            elif event_type == "command_sent":
                icon = "📤"
                color = "yellow"
                prefix = "CMD SENT"
            elif event_type == "command_output":
                icon = "📥"
                color = "cyan"
                prefix = "CMD OUT"
            elif event_type == "command_error":
                icon = "⚠️"
                color = "bright_red"
                prefix = "CMD ERR"
            elif event_type == "download":
                icon = "⬇️"
                color = "bright_blue"
                prefix = "DOWNLOAD"
            elif event_type == "upload":
                icon = "⬆️"
                color = "bright_magenta"
                prefix = "UPLOAD"
            elif event_type == "disconnect":
                icon = "❌"
                color = "bright_red"
                prefix = "DISCONN"
            elif event_type == "warning":
                icon = "⚠️"
                color = "yellow"
                prefix = "WARNING"
            elif event_type == "error":
                icon = "❗"
                color = "red"
                prefix = "ERROR"
            elif event_type == "success":
                icon = "✅"
                color = "green"
                prefix = "SUCCESS"
            elif event_type == "info":
                icon = "ℹ️"
                color = "bright_blue"
                prefix = "INFO"
            else:
                icon = "•"
                color = "white"
                prefix = "EVENT"
            
            event_entry = {
                "timestamp": timestamp,
                "icon": icon,
                "color": color,
                "prefix": prefix,
                "message": message,
                "details": details or {}
            }
            
            self.events.append(event_entry)
            self.stats["last_activity"] = timestamp
            
            # Trigger update immediately
            # if self.active:
            #     self._refresh_header_display()

    def update_stats(self, sessions: int, beacons: int):
        """
        Update connection statistics.
        
        Args:
            sessions: Number of active sessions
            beacons: Number of active beacons
        """
        with self.lock:
            self.stats["sessions"] = sessions
            self.stats["beacons"] = beacons
            self.stats["total_connections"] = sessions + beacons

            # Trigger update immediately
            # if self.active:
            #     self._refresh_header_display()
    
    def _get_uptime_str(self) -> str:
        """Get formatted uptime string."""
        uptime = datetime.now() - self.stats["server_uptime"]
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
    def _create_stats_panel(self) -> Panel:
        """Create the statistics panel."""
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="bright_cyan bold", justify="right", width=16)
        stats_table.add_column(style="bright_white", justify="left")
        
        # Connection statistics
        session_color = "bright_green bold" if self.stats['sessions'] > 0 else "dim"
        beacon_color = "bright_cyan bold" if self.stats['beacons'] > 0 else "dim"
        total_color = "bright_magenta bold" if self.stats['total_connections'] > 0 else "dim"
        
        stats_table.add_row(
            "🔗 Sessions:",
            f"[{session_color}]{self.stats['sessions']}[/]"
        )
        stats_table.add_row(
            "📡 Beacons:",
            f"[{beacon_color}]{self.stats['beacons']}[/]"
        )
        stats_table.add_row(
            "📊 Total:",
            f"[{total_color}]{self.stats['total_connections']}[/]"
        )
        stats_table.add_row("", "")  # Spacer
        stats_table.add_row(
            "⏱️  Uptime:",
            f"[bright_yellow]{self._get_uptime_str()}[/]"
        )
        stats_table.add_row(
            "🕐 Last Activity:",
            f"[dim]{self.stats['last_activity']}[/]"
        )
        
        return Panel(
            Align.center(stats_table, vertical="middle"),
            title="[bold bright_magenta]╣ CONNECTION STATS ╠[/]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(0, 1),
            height=12
        )
    
    def _create_activity_panel(self) -> Panel:
        """Create the activity feed panel."""
        if not self.events:
            empty_text = Text("Waiting for activity...", style="dim italic")
            return Panel(
                Align.center(empty_text, vertical="middle"),
                title="[bold bright_cyan]╣ LATEST EVENTS ╠[/]",
                border_style="bright_cyan",
                box=box.ROUNDED,
                padding=(0, 1),
                height=12
            )
        
        # Create activity table
        activity_table = Table.grid(padding=(0, 1))
        activity_table.add_column(style="dim", width=8, no_wrap=True)  # Time
        activity_table.add_column(width=2, no_wrap=True)  # Icon
        activity_table.add_column(style="bold", width=10, no_wrap=True)  # Prefix
        activity_table.add_column()  # Message
        
        # Show events in reverse order (newest first), limit to last 8 to fit
        for event in list(reversed(list(self.events)))[:8]:
            activity_table.add_row(
                f"[dim]{event['timestamp']}[/]",
                event['icon'],
                f"[{event['color']}]{event['prefix']}[/]",
                f"[{event['color']}]{event['message']}[/]"
            )
        
        return Panel(
            activity_table,
            title="[bold bright_cyan]╣ LATEST EVENTS ╠[/]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            height=12
        )
    
    def get_header_display(self):
        """Get the complete header display (stats + activity in columns)."""
        # No lock here to avoid deadlock with recursive calls
        stats_panel = self._create_stats_panel()
        activity_panel = self._create_activity_panel()
        return Columns([stats_panel, activity_panel], equal=True, expand=True)
        
    def _refresh_header_display(self):
        """Redraw the header at the top of the screen."""
        if not self.active:
            return
            
        try:
            # Generate header content
            with self.console.capture() as capture:
                self.console.print(self.get_header_display())
            header_str = capture.get()
            
            # Use ANSI escape codes to update header area
            # 1. Save cursor position (\0337 for DECSC)
            # 2. Hide cursor (\033[?25l)
            # 3. Move cursor to home (\033[H)
            # 4. Print header
            # 5. Restore cursor (\033[?25h)
            # 6. Restore cursor position (\0338 for DECRC)
            
            # Write directly to __stdout__ to bypass prompt_toolkit
            sys.__stdout__.write(f"\0337\033[?25l\033[H{header_str}\033[?25h\0338")
            sys.__stdout__.flush()
        except Exception:
            pass
            
    def _update_loop(self):
        """Background loop to update uptime and stats."""
        while self.active and not self.should_stop:
            self._refresh_header_display()
            time.sleep(1)

    def _setup_scrolling_region(self):
        """Set terminal scrolling region to exclude header."""
        # Get terminal size directly to be sure
        try:
            ts = os.get_terminal_size()
            h = ts.lines
        except:
            h = self.console.size.height
            
        # Calculate header height accurately
        with self.console.capture() as capture:
             self.console.print(self.get_header_display())
        header_str = capture.get()
        self.header_height = len(header_str.splitlines())
        
        # Reserve header + 1 line margin
        top_margin = self.header_height + 2
        
        # Only set if we have space
        if h > top_margin:
            sys.__stdout__.write(f"\033[{top_margin};{h}r")  # Set scrolling region
            sys.__stdout__.write(f"\033[{top_margin};1H")    # Move cursor to start of scrolling region
            sys.__stdout__.flush()

    def start_display(self):
        """Start the display (Banner only, Live stats moved to bottom toolbar)."""
        if self.active:
            return
            
        self.active = True
        self.should_stop = False
        
        # Clear screen for clean start (ANSI)
        sys.__stdout__.write("\033[2J\033[H")
        sys.__stdout__.flush()
        
        # Print header first time manually
        with self.console.capture() as capture:
            self.console.print(self.get_header_display())
        header_str = capture.get()
        sys.__stdout__.write(header_str)
        sys.__stdout__.flush()
        
        # Setup scrolling region
        self._setup_scrolling_region()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
    def stop_display(self):
        """Stop the display."""
        self.should_stop = True
        self.active = False
        self._reset_scrolling_region()
        # Cleanup if needed

    
    def print_banner(self):
        """Print a stylish startup banner."""
        banner_text = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║     ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗   ║
║     ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║   ║
║     ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║   ║
║     ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║   ║
║     ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║   ║
║     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ║
║                                                                       ║
║                    PROMETHEAN PROXY - C2 SERVER                      ║
║                         Command & Control v2.0                       ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner_text, style="bold bright_cyan")
        self.console.print()
        
    def print_activity_sidebar(self):
        """Print the current activity sidebar (for manual status command)."""
        try:
            display = self.get_header_display()
            self.console.print(display)
        except Exception as e:
            # Fallback to simple display if rendering fails
            self.console.print(f"[yellow]Activity display error: {e}[/]")

    def print_prompt_hint(self, available_commands: List[str]):
        """Print a hint showing available commands."""
        commands_str = ", ".join(f"[bright_cyan]{cmd}[/]" for cmd in available_commands[:8])
        hint = f"[dim]💡 Available: {commands_str}...[/]"
        self.console.print(hint)

    def get_bottom_toolbar(self):
        """Get the bottom toolbar content for prompt_toolkit"""
        uptime = self._get_uptime_str()
        
        # Color styles with simple HTML for prompt_toolkit
        # Stats
        s_count = self.stats['sessions']
        b_count = self.stats['beacons']
        t_count = self.stats['total_connections']
        
        s_color = "ansigreen" if s_count > 0 else "ansigray"
        b_color = "ansicyan" if b_count > 0 else "ansigray" 
        
        # Last event
        last_event = "No activity"
        if self.events:
            evt = self.events[-1]
            last_event = f"{evt['icon']} {evt['message']}"

        return HTML(
            f" <b>PROMETHEAN</b> | "
            f"Sessions: <style fg='{s_color}'><b>{s_count}</b></style> | "
            f"Beacons: <style fg='{b_color}'><b>{b_count}</b></style> | "
            f"Uptime: <style fg='ansiyellow'>{uptime}</style>"
        )

    def clear_screen(self):
        """Clear the interactive area and reset the display."""
        if not self.active:
            # Fallback
            sys.__stdout__.write("\033[2J\033[H")
            sys.__stdout__.flush()
            return

        # Re-calculate layout and clear only the scrolling region
        self._setup_scrolling_region()
        
        # Cursor is now at the top of the scrolling region (set by _setup_scrolling_region)
        # Clear from cursor to end of screen
        sys.__stdout__.write("\033[0J")
        
        # Force a header refresh
        self._refresh_header_display()
        
        sys.__stdout__.flush()


# Global UI manager instance
_ui_manager: Optional[UIManager] = None


def get_ui_manager() -> UIManager:
    """Get or create the global UI manager instance."""
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = UIManager()
    return _ui_manager


def log_connection_event(event_type: str, message: str, details: Optional[Dict] = None):
    """
    Convenience function to log a connection event to the UI.
    
    Args:
        event_type: Type of event (session, beacon, disconnect, command, etc.)
        message: Event message
        details: Optional additional details
    """
    ui_manager = get_ui_manager()
    ui_manager.add_event(event_type, message, details)
    
    # Don't print updated sidebar automatically - let the main loop handle it
    # This prevents excessive output and maintains cleaner terminal flow


def update_connection_stats(sessions: int, beacons: int):
    """
    Convenience function to update connection statistics.
    
    Args:
        sessions: Number of active sessions
        beacons: Number of active beacons
    """
    ui_manager = get_ui_manager()
    ui_manager.update_stats(sessions, beacons)
