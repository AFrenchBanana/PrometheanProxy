import readline

import colorama

from ...global_objects import logger, tab_completion
from ...utils.console import colorize
from ...utils.ui_manager import RichPrint


class UtilityHandler:
    """
    Handles utility commands for the multi-handler module.
    """

    def view_logs(self) -> None:
        """
        Views log messages with optional filtering by level.
        """
        try:
            count_input = self.prompt_session.prompt(
                "How many lines to view? [Default: 100]: "
            )
            count = int(count_input) if count_input.isdigit() else 100
        except ValueError:
            logger.warning("Invalid input for log count, defaulting to 100.")
            count = 100

        if count < 0:
            RichPrint.r_print(colorize("Line count cannot be negative.", fg="red"))
            return

        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            )
        )
        level = (
            self.prompt_session.prompt(
                "Filter by level (DEBUG, INFO, etc.) or press Enter for all: "
            )
            .upper()
            .strip()
        )

        logs = logger.view(count, level if level else None)
        log_level_str = f"level '{level}'" if level else "all levels"
        logger.info(f"Retrieved {len(logs)} log messages for {log_level_str}")

        if not logs:
            RichPrint.r_print(
                colorize("No logs found for the specified criteria.", fg="yellow")
            )
        if not logs:
            RichPrint.r_print(colorize("No logs found for the specified criteria.", fg='yellow'))
            return

        for log in logs:
            # Colorize based on level
            if "ERROR" in log or "CRITICAL" in log:
                RichPrint.r_print(colorize(log.rstrip("\n"), fg="red"))
            elif "WARNING" in log:
                RichPrint.r_print(colorize(log.rstrip("\n"), fg="yellow"))
            else:
                RichPrint.r_print(colorize(log.rstrip("\n"), fg="white"))

        logger.info("Displayed log messages to user.")
        return
