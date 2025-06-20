import logging
import os
import sys
from logging import Logger as PyLogger, getLevelName
from logging import handlers

# Import colorama and initialize it
import colorama
from colorama import Fore, Style


class ColoramaFormatter(logging.Formatter):
    """
    A custom log formatter that adds color to console output using colorama.
    """
    def __init__(self, fmt: str, datefmt: str):
        super().__init__(fmt, datefmt)
        # Define colors for each log level
        self.FORMATS = {
            logging.DEBUG: Fore.CYAN,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.RED + Style.BRIGHT,
        }

    def format(self, record):
        # Get the color for the current log level
        color = self.FORMATS.get(record.levelno, "")

        # Let the parent class do the actual formatting
        output = super().format(record)
        # Prepend the color code. Style.RESET_ALL is handled by colorama.init()
        return color + output


class LoggingClass:
    """
    Wrapper around Python's logging module with file rotation,
    in-memory viewing, and colored console output via colorama.

    Usage:
        # Log to console with colors
        log_console = LoggingClass(name="console_app", level="DEBUG")
        log_console.info("This info message will be green.")
        log_console.warning("This warning will be yellow.")
        # Log to a file (no colors are written to the file)
        log_file = LoggingClass(name="file_app", log_file="app.log")
        log_file.error("This error is written plainly to app.log.")

        # View recent logs (defaults to INFO level and above)
        print("\n--- Viewing recent logs (default level is INFO) ---")
        for message in log_console.view(count=5):
            # The view method also returns colored output if the logger targets the console
            print(message)
    """
    def __init__(
        self,
        name: str,
        log_file: str = None,
        level: str = "INFO",
        fmt: str = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        max_size: int = 1048576,  # 1MB
        memory_capacity: int = 1000
    ):
        # Initialize colorama to make ANSI codes work on all platforms
        # autoreset=True ensures that the color is reset after each print statement
        colorama.init(autoreset=True)

        self.logger: PyLogger = logging.getLogger(name)
        self.logger.setLevel(level.upper())
        self.memory_handler = None

        if not self.logger.handlers:
            # Choose formatter: ColoramaFormatter for interactive consoles, standard for files
            if log_file or not sys.stdout.isatty():
                formatter = logging.Formatter(fmt, datefmt)
            else:
                formatter = ColoramaFormatter(fmt, datefmt)

            # Determine the target handler (file or console)
            if log_file:
                # Create and attach a file handler in append mode for file logging
                dirpath = os.path.dirname(log_file)
                if dirpath:
                    os.makedirs(dirpath, exist_ok=True)
                file_handler = logging.FileHandler(log_file, mode='a')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            else:
                # Always attach a console handler for immediate output
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

                # Memory handler used only for view() without auto-flush
                self.memory_handler = handlers.MemoryHandler(
                    capacity=memory_capacity,
                    flushLevel=logging.CRITICAL + 1,  # no auto-flush
                    target=None
                )
                self.memory_handler.setFormatter(formatter)
                self.logger.addHandler(self.memory_handler)

    def __getattr__(self, name):
        """Pass logging methods (debug, info, etc.) directly to the logger instance."""
        if name in ['debug', 'info', 'warning', 'error', 'critical', 'exception']:
            return getattr(self.logger, name)
        self.logger.warning(
            f"Attempted to access an invalid logging method: {name}. "
            "Returning a no-op function."
        )

    def view(self, count: int, level: str = None) -> list[str]:
        """
        Returns the last 'count' log messages from memory.
        Defaults to the INFO level if 'level' is not specified.

        Args:
            count (int): The maximum number of log messages to retrieve.
            level (str, optional): The minimum logging level to filter by.
                                   Defaults to "INFO" if None or invalid.

        Returns:
            list[str]: A list of formatted (and possibly colored) log messages.
        """

        if not self.memory_handler:
            self.logger.error("Memory handler is not configured. Cannot view logs.")
            return ["Logger not configured with a memory handler."]

        # **FIX**: Default to "INFO" if level is None or an empty string
        log_level_str = (level or "INFO").upper()
        numeric_level = getLevelName(log_level_str)
        logging
        # If the provided level string was invalid, default to INFO
        if not isinstance(numeric_level, int):
            print(f"{Fore.YELLOW}Warning: Invalid log level '{level}' for view(). Defaulting to 'INFO'.")
            numeric_level = getLevelName("INFO")
        matching_records = [
            self.memory_handler.formatter.format(record)
            for record in self.memory_handler.buffer
            if record.levelno >= numeric_level
        ]

        return matching_records[-count:]

    def flush(self):
        """Manually flushes the logs from memory to the target handler."""
        self.logger.debug("Flushing memory handler logs to target handler.")
        if self.memory_handler:
            self.memory_handler.flush()
