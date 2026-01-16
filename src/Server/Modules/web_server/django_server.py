"""
Django Web Server Module for PrometheanProxy
==============================================
This module integrates the Django web interface into the MultiHandler system,
allowing it to run as a daemon thread alongside the beacon server and other
PrometheanProxy components.
"""

import os
import sys
import threading
from pathlib import Path

import django


def setup_django_environment():
    """
    Set up the Django environment for running within the MultiHandler.

    Returns:
        Path: The Django project directory path
    """
    # Get the web directory path
    server_dir = Path(__file__).resolve().parent.parent.parent
    web_dir = server_dir / "web"

    # Add web directory to Python path if not already there
    web_dir_str = str(web_dir)
    if web_dir_str not in sys.path:
        sys.path.insert(0, web_dir_str)

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promethean_web.settings")

    return web_dir


def run_django_server(config):
    """
    Start the Django web server using Daphne (ASGI server with WebSocket support).

    This function runs in a separate thread and starts the Django web interface
    on the configured host and port. It uses Daphne to support both HTTP and
    WebSocket connections for real-time updates.

    Args:
        config (dict): Configuration dictionary containing server settings

    Returns:
        None
    """
    from Modules.global_objects import logger

    try:
        # Set up Django environment
        web_dir = setup_django_environment()

        # Get configuration from config dict
        web_config = config.get("web_server", {})
        host = web_config.get("host", "0.0.0.0")
        port = web_config.get("port", 8000)
        use_ssl = web_config.get("use_ssl", False)

        logger.info(f"Initializing Django web server on {host}:{port}")

        # Initialize Django
        try:
            django.setup()
            logger.info("Django initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Django: {e}")
            return

        # Import Daphne components after Django is set up
        try:
            import argparse

            from daphne.cli import CommandLineInterface
            from daphne.endpoints import build_endpoint_description_strings
            from daphne.server import Server
        except ImportError:
            logger.error("Daphne is not installed. Install with: pip install daphne")
            logger.error("Web server cannot start without Daphne")
            return

        # Import ASGI application
        try:
            from promethean_web.asgi import application
        except ImportError as e:
            logger.error(f"Failed to import ASGI application: {e}")
            return

        # Build endpoint description
        endpoints = build_endpoint_description_strings(
            host=host, port=port, unix_socket=None
        )

        logger.info(f"Starting Django web server (Daphne) on http://{host}:{port}")
        logger.info("Web interface will be available at the configured address")

        # Create and run Daphne server
        try:
            server = Server(
                application=application,
                endpoints=endpoints,
                verbosity=1,
                proxy_headers=True,
                server_name="PrometheanProxy-Web",
            )

            logger.info("Django web server started successfully")
            logger.info(f"Access the web interface at: http://{host}:{port}")

            # This will block until the server is stopped
            server.run()

        except Exception as e:
            logger.error(f"Daphne server error: {e}")
            import traceback

            logger.error(traceback.format_exc())

    except KeyboardInterrupt:
        logger.info("Django web server received shutdown signal")
    except Exception as e:
        logger.error(f"Django web server error: {e}")
        import traceback

        logger.error(traceback.format_exc())


def start_django_server(config):
    """
    Start the Django web server in a separate daemon thread.

    This is the main entry point called from server.py to start the Django
    web interface alongside other PrometheanProxy components.

    Args:
        config (dict): Configuration dictionary containing server settings

    Returns:
        threading.Thread: The thread object running the Django server
    """
    from Modules.global_objects import logger

    # Check if web server is enabled in config
    web_config = config.get("web_server", {})
    enabled = web_config.get("enabled", False)

    if not enabled:
        logger.info("Django web server is disabled in configuration")
        return None

    logger.info("Starting Django web server thread")

    # Start Django server in a daemon thread
    server_thread = threading.Thread(
        target=run_django_server, args=(config,), daemon=True, name="DjangoWebServer"
    )
    server_thread.start()

    return server_thread
