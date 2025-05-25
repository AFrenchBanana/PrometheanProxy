import logging
import os
from logging import Logger as PyLogger
from logging import handlers

class LoggingClass:
    """
    Wrapper around Python's logging module with file size-based rotation.
    Usage:
        # Log file will rotate when it reaches 1MB (1,000,000 bytes)
        # and keep one backup file.
        log = LoggingClass(name="app", log_file="app.log", level="DEBUG", max_length=1_000_000)
        log.info("Started")
    """

    def __init__(
        self,
        name: str,
        log_file: str = None,
        level: str = "INFO",
        fmt: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        max_size: int = 1048576 # Default to 1MB (1024 * 1024 bytes)
    ):
        """
        Initializes the LoggingClass.

        Args:
            name (str): The name of the logger.
            log_file (str, optional): The path to the log file. If None, logs go to console. Defaults to None.
            level (str, optional): The logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"). Defaults to "INFO".
            fmt (str, optional): The format string for log messages. Defaults to "%(asctime)s %(levelname)s [%(name)s] %(message)s".
            datefmt (str, optional): The date format string. Defaults to "%Y-%m-%d %H:%M:%S".
            max_length (int, optional): The maximum size of the log file in bytes before rotation.
                                        Defaults to 1MB (1048576 bytes).
        """
        self.logger: PyLogger = logging.getLogger(name)
        self.logger.setLevel(level.upper())

        # Prevent adding multiple handlers if the logger is retrieved multiple times
        # This is important for preventing duplicate log messages.
        if not self.logger.handlers:
            formatter = logging.Formatter(fmt, datefmt)

            if log_file:
                dirpath = os.path.dirname(log_file)
                if dirpath:
                    os.makedirs(dirpath, exist_ok=True)

                # Use RotatingFileHandler for log rotation
                # maxBytes: The maximum size of the file before rotation (in bytes)
                # backupCount: The number of backup files to keep. 1 means current + one .1 file.
                file_hdl = handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=max_size,
                    backupCount=1 # Keep one old log file (e.g., app.log.1)
                )
                file_hdl.setLevel(level.upper())
                file_hdl.setFormatter(formatter)
                self.logger.addHandler(file_hdl)
            else:
                # If no log_file is specified, log to console
                console_hdl = logging.StreamHandler()
                console_hdl.setLevel(level.upper())
                console_hdl.setFormatter(formatter)
                self.logger.addHandler(console_hdl)

    def debug(self, msg: str, *args, **kwargs):
        """Logs a message with DEBUG level."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Logs a message with INFO level."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Logs a message with WARNING level."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Logs a message with ERROR level."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Logs a message with CRITICAL level."""
        self.logger.critical(msg, *args, **kwargs)
