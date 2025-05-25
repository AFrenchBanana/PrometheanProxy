import logging
import os
from logging import Logger as PyLogger


class LoggingClass:
    """
    Wrapper around Python's logging module.
    Usage:
        log = LoggingClass(name="app", log_file="app.log", level="DEBUG")
        log.info("Started")
    """

    def __init__(
        self,
        name: str,
        log_file: str = None,
        level: str = "INFO",
        fmt: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S"
    ):
        self.logger: PyLogger = logging.getLogger(name)
        self.logger.setLevel(level.upper())

        formatter = logging.Formatter(fmt, datefmt)

        if log_file:
            dirpath = os.path.dirname(log_file)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            file_hdl = logging.FileHandler(log_file)
            file_hdl.setLevel(level.upper())
            file_hdl.setFormatter(formatter)
            self.logger.addHandler(file_hdl)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)