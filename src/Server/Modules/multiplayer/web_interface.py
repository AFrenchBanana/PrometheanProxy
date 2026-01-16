"""
Web Interface Launcher for PrometheanProxy

This module provides integration between the Django web interface
and the PrometheanProxy multiplayer server. It launches the web
interface in a separate thread and manages its lifecycle.
"""

import logging
import os
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class WebInterface:
    """
    Manages the Django web interface integration with PrometheanProxy.

    This class handles:
    - Starting the Django web server in a separate thread
    - Configuring the web interface to use the multiplayer server
    - Managing the lifecycle of the web interface
    """

    def __init__(self, config):
        """
        Initialize the web interface manager.

        Args:
            config: Server configuration dictionary
        """
        self.config = config
        self.web_thread = None
        self.daphne_process = None
        self.is_running = False

        # Determine web interface directory
        server_dir = Path(__file__).resolve().parent.parent.parent
        self.web_dir = server_dir / "web"

        # Web interface settings
        self.web_enabled = config.get("multiplayer", {}).get("webInterface", False)
        self.web_host = config.get("multiplayer", {}).get("webHost", "0.0.0.0")
        self.web_port = config.get("multiplayer", {}).get("webPort", 8000)

        logger.info(f"Web interface directory: {self.web_dir}")
        logger.info(f"Web interface enabled: {self.web_enabled}")

    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.

        Returns:
            bool: True if all dependencies are available
        """
        missing = []
        try:
            import django
        except ImportError:
            missing.append("django")

        try:
            import rest_framework
        except ImportError:
            missing.append("djangorestframework")

        try:
            import channels
        except ImportError:
            missing.append("channels")

        try:
            import daphne
        except ImportError:
            missing.append("daphne")

        try:
            import redis
        except ImportError:
            missing.append("redis")

        if missing:
            logger.error(f"Web interface dependencies missing: {', '.join(missing)}")
            logger.error("Install with: pip install -r web_requirements.txt")
            logger.error(
                "Or: pip install django djangorestframework channels daphne redis django-cors-headers channels-redis"
            )
            return False

        logger.info("Web interface dependencies found")
        return True

    def _check_redis(self) -> bool:
        """
        Check if Redis is available for WebSocket support.

        Returns:
            bool: True if Redis is running
        """
        try:
            import redis

            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                socket_timeout=2,
            )
            r.ping()
            logger.info("Redis connection successful")
            return True
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            logger.warning("WebSocket features will be limited")
            return False

    def _setup_environment(self):
        """Configure environment variables for Django."""
        # Add web directory to Python path
        if str(self.web_dir) not in sys.path:
            sys.path.insert(0, str(self.web_dir))

        # Set Django settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promethean_web.settings")

        # Set environment variables from config
        if not os.getenv("PROMETHEAN_API_URL"):
            # Build API URL from multiplayer server config
            mp_host = self.config["multiplayer"].get(
                "multiplayerListenAddress", "localhost"
            )
            mp_port = self.config["multiplayer"].get("multiplayerPort", 8443)
            # Use localhost if listening on 0.0.0.0
            if mp_host == "0.0.0.0":
                mp_host = "localhost"
            os.environ["PROMETHEAN_API_URL"] = f"https://{mp_host}:{mp_port}"

        if not os.getenv("PROMETHEAN_API_VERIFY_SSL"):
            os.environ["PROMETHEAN_API_VERIFY_SSL"] = "False"

        logger.info(f"Backend API URL: {os.environ.get('PROMETHEAN_API_URL')}")

    def _run_migrations(self):
        """Run Django database migrations."""
        try:
            import django
            from django.core.management import execute_from_command_line

            django.setup()
            logger.info("Running database migrations...")

            # Save original argv
            original_argv = sys.argv

            # Run migrations
            sys.argv = ["manage.py", "migrate", "--noinput"]
            execute_from_command_line(sys.argv)

            # Restore original argv
            sys.argv = original_argv

            logger.info("Database migrations completed")
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    def _run_daphne_server(self):
        """Run the Daphne ASGI server for WebSocket support."""
        try:
            import django

            django.setup()

            from daphne.cli import CommandLineInterface

            logger.info(f"Starting Daphne server on {self.web_host}:{self.web_port}")

            # Configure Daphne
            cli = CommandLineInterface()
            sys.argv = [
                "daphne",
                "-b",
                self.web_host,
                "-p",
                str(self.web_port),
                "promethean_web.asgi:application",
            ]

            cli.run(sys.argv[1:])

        except Exception as e:
            logger.error(f"Daphne server error: {e}")
            self.is_running = False

    def _run_django_server(self):
        """Run the Django development server (fallback if Daphne not available)."""
        try:
            import django
            from django.core.management import execute_from_command_line

            django.setup()

            logger.info(f"Starting Django server on {self.web_host}:{self.web_port}")
            logger.warning("Using Django dev server - WebSockets may be limited")

            # Run server
            sys.argv = [
                "manage.py",
                "runserver",
                f"{self.web_host}:{self.web_port}",
                "--noreload",  # Important: prevent auto-reloader in thread
            ]
            execute_from_command_line(sys.argv)

        except Exception as e:
            logger.error(f"Django server error: {e}")
            self.is_running = False

    def start(self):
        """Start the web interface in a background thread."""
        if not self.web_enabled:
            logger.info("Web interface is disabled in configuration")
            return False

        if self.is_running:
            logger.warning("Web interface is already running")
            return False

        # Check if web directory exists
        if not self.web_dir.exists():
            logger.error(f"Web interface directory not found: {self.web_dir}")
            logger.error("Please ensure the web interface is properly installed")
            return False

        # Check dependencies
        if not self._check_dependencies():
            logger.error("Web interface dependencies not met")
            return False

        # Check Redis (optional but recommended)
        self._check_redis()

        # Setup environment
        self._setup_environment()

        # Run migrations
        if not self._run_migrations():
            logger.warning("Migration issues detected, continuing anyway")

        # Change to web directory
        original_cwd = os.getcwd()
        os.chdir(self.web_dir)

        # Start web server in a thread
        try:
            # Try to use Daphne for WebSocket support
            try:
                import daphne

                server_func = self._run_daphne_server
                logger.info("Using Daphne ASGI server (WebSocket support enabled)")
            except ImportError:
                logger.warning(
                    "Daphne not available, falling back to Django dev server"
                )
                logger.warning("WebSocket features will be limited")
                server_func = self._run_django_server

            self.web_thread = threading.Thread(
                target=server_func, daemon=True, name="WebInterface"
            )

            self.web_thread.start()
            self.is_running = True

            logger.info("=" * 60)
            logger.info(
                f"Web interface started on http://{self.web_host}:{self.web_port}"
            )
            logger.info(
                f"Access the web interface at: http://localhost:{self.web_port}"
            )
            logger.info(f"Login with your multiplayer server credentials")
            logger.info("=" * 60)

            # Restore original directory
            os.chdir(original_cwd)

            return True

        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            logger.exception("Web interface startup error details:")
            os.chdir(original_cwd)
            return False

    def stop(self):
        """Stop the web interface."""
        if not self.is_running:
            return

        logger.info("Stopping web interface...")
        self.is_running = False

        # Note: The thread is daemon, so it will be killed when the main process exits
        # For a graceful shutdown, we'd need to implement a proper shutdown mechanism

        logger.info("Web interface stopped")

    def get_status(self) -> dict:
        """
        Get the current status of the web interface.

        Returns:
            dict: Status information
        """
        return {
            "enabled": self.web_enabled,
            "running": self.is_running,
            "host": self.web_host,
            "port": self.web_port,
            "url": f"http://{self.web_host}:{self.web_port}"
            if self.is_running
            else None,
            "thread_alive": self.web_thread.is_alive() if self.web_thread else False,
        }
