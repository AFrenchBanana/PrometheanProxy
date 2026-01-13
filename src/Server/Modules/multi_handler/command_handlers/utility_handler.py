import os
import readline

import colorama

from ...global_objects import logger, plugin_dir, tab_completion
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
            RichPrint.r_print(
                colorize("No logs found for the specified criteria.", fg="yellow")
            )
            return

        for log in logs:
            # Colorize based on level
            if "ERROR" in log or "CRITICAL" in log:
                RichPrint.r_print(colorize(log.rstrip("\n"), fg="red"))
            elif "WARNING" in log:
                RichPring.r_print(colorize(log.rstrip("\n"), fg="yellow"))
            else:
                RichPrint.r_print(colorize(log.rstrip("\n"), fg="white"))

        logger.info("Displayed log messages to user.")
        return

    def plugins(self) -> None:
        """
        Lists all available plugins and their supported operating systems.
        """
        plugins_dir = os.path.expanduser(self.config["server"]["module_location"])

        if not os.path.isdir(plugins_dir):
            RichPrint.r_print(
                colorize(f"Plugin directory not found at: {plugins_dir}", fg="red")
            )
            return

        RichPrint.r_print(colorize(f"%-20s %-10s" % ("Plugin", "OS"), bold=True))
        RichPrint.r_print(colorize(f"%-20s %-10s" % ("------", "--"), bold=True))

        for plugin_name in sorted(os.listdir(plugins_dir)):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            if (
                os.path.isdir(plugin_path)
                and plugin_name != "template"
                and not plugin_name.endswith("__pycache__")
            ):
                go_file = os.path.join(plugin_path, "main.go")
                if os.path.exists(go_file):
                    with open(go_file, "r") as f:
                        for line in f:
                            if "GOOS:" in line:
                                os_support = line.split(":")[-1].strip()
                                RichPrint.r_print(
                                    f"%-20s %-10s" % (plugin_name, os_support)
                                )
                                break
                        else:
                            RichPrint.r_print(f"%-20s %-10s" % (plugin_name, "N/A"))
                else:
                    RichPrint.r_print(f"%-20s %-10s" % (plugin_name, "python"))
        return
