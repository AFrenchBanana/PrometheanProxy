from ...global_objects import logger, tab_completion

import colorama
import readline


class UtilityHandler:
    """Handles utility commands like viewing logs."""

    def view_logs(self) -> None:
        """
        View the logs stored in the log file, with options for count and level.
        """
        logger.info("Viewing logs")
        try:
            count_input = input("How many lines to view? [Default: 100]: ")
            count = int(count_input) if count_input.isdigit() else 100
        except ValueError:
            logger.warning("Invalid input for log count, defaulting to 100.")
            count = 100
        
        if count < 0:
            print(colorama.Fore.RED + "Line count cannot be negative.")
            return
            
        readline.set_completer(
            lambda text, state: tab_completion(
                text, state, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))
        level = input("Filter by level (DEBUG, INFO, etc.) or press Enter for all: ").upper().strip()
        
        logs = logger.view(count, level if level else None)
        log_level_str = f"level '{level}'" if level else "all levels"
        logger.info(f"Retrieved {len(logs)} log messages for {log_level_str}")
        
        if not logs:
            print(colorama.Fore.YELLOW + "No logs found for the specified criteria.")
            return

        for log in logs:
            # Colorize based on level
            if "ERROR" in log or "CRITICAL" in log:
                print(colorama.Fore.RED + log, end='')
            elif "WARNING" in log:
                print(colorama.Fore.YELLOW + log, end='')
            else:
                print(colorama.Fore.WHITE + log, end='')
            
        logger.info("Displayed log messages to user.")
        return