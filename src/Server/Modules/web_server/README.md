# Django Web Server Module

This module integrates the Django web interface into the PrometheanProxy MultiHandler system, allowing it to run as a daemon thread alongside other server components.

## Overview

The Django web server provides a modern web interface for managing PrometheanProxy operations, including:
- Real-time connection monitoring via WebSockets
- Session and beacon management
- Command history and logs
- REST API for programmatic access
- User authentication and authorization

## Architecture

The web server runs as a separate daemon thread within the MultiHandler process, similar to the beacon server. It uses:
- **Django**: Web framework
- **Daphne**: ASGI server with WebSocket support
- **Django Channels**: WebSocket handling with in-memory channel layer (no Redis required for development)
- **Django REST Framework**: API endpoints

## Configuration

Web server settings are defined in `config.toml`:

```toml
[web_server]
# Django web interface settings
enabled = true
host = "0.0.0.0"
port = 8001
use_ssl = false
```

### Configuration Options

- `enabled`: Enable/disable the web server (default: `true`)
- `host`: Listen address (default: `"0.0.0.0"`)
- `port`: Port number (default: `8001`)
- `use_ssl`: Enable SSL/TLS (default: `false`, future feature)

## Usage

### Starting the Server

The web server starts automatically when you run the main PrometheanProxy server:

```bash
cd src/Server
python server.py
```

The web interface will be available at: `http://localhost:8001`

### Disabling the Web Server

To disable the web server, set `enabled = false` in `config.toml`:

```toml
[web_server]
enabled = false
```

## Integration Details

### Thread Lifecycle

The web server is started in `server.py` as a daemon thread:

```python
from Modules.web_server import start_django_server

# Start Django web server
django_thread = start_django_server(config)
```

As a daemon thread, it will automatically shut down when the main MultiHandler process exits.

### Django Environment Setup

The module automatically:
1. Adds the `web/` directory to Python's path
2. Sets the `DJANGO_SETTINGS_MODULE` environment variable
3. Initializes Django with `django.setup()`
4. Starts the Daphne ASGI server

### Channel Layer Configuration

The Django web interface uses an **in-memory channel layer** for WebSocket support. This means:
- ✅ No Redis dependency required
- ✅ Works out of the box for development
- ✅ Perfect for single-server deployments
- ⚠️ WebSocket connections don't persist across server restarts
- ⚠️ Won't work for multi-server deployments (use Redis for that)

## Development

### Running Migrations

Before first use, run Django migrations:

```bash
cd src/Server/web
python manage.py migrate
```

### Creating Admin User

Create a superuser for the Django admin:

```bash
cd src/Server/web
python manage.py createsuperuser
```

### Standalone Development Mode

For frontend development, you can run the Django server standalone:

```bash
cd src/Server/web
python manage.py runserver 8001
```

Or use the provided startup script:

```bash
cd src/Server/web
./start_web.sh
```

## Dependencies

Required Python packages (installed via `web_requirements.txt`):
- Django
- daphne
- channels
- djangorestframework
- djangorestframework-simplejwt
- django-cors-headers
- python-dotenv

## Troubleshooting

### Web Server Not Starting

1. **Check if enabled**: Verify `enabled = true` in `config.toml`
2. **Check logs**: Look for Django-related errors in server logs
3. **Port conflicts**: Ensure port 8001 (or configured port) is not in use
4. **Dependencies**: Install web requirements: `pip install -r web_requirements.txt`

### Connection Timeout Issues

If Django was timing out before:
- **Fixed**: The in-memory channel layer eliminates Redis dependency
- **Previous issue**: Redis was required but not running
- **Current solution**: Works without Redis for development

### WebSocket Issues

If WebSockets aren't working:
1. Ensure Daphne is installed: `pip install daphne`
2. Check that channels is configured with in-memory layer
3. Verify ASGI application is being used (not WSGI)

## Production Considerations

For production deployments:

1. **Use a reverse proxy** (nginx/Apache) in front of Django
2. **Enable SSL/TLS** for secure connections
3. **Use environment variables** for sensitive settings
4. **Consider Redis** if scaling to multiple servers
5. **Set DEBUG=False** in production
6. **Use proper SECRET_KEY** (not the default)
7. **Configure ALLOWED_HOSTS** appropriately

## File Structure

```
web_server/
├── __init__.py              # Module exports
├── django_server.py         # Main integration logic
└── README.md                # This file
```

## API Integration

The web interface integrates with the PrometheanProxy backend via:
- Direct Python imports (shares the same process)
- Access to `global_objects` (config, logger, sessions, beacons)
- Real-time updates via WebSockets
- REST API for external clients

## Future Enhancements

- SSL/TLS support (use_ssl configuration)
- Redis integration option for production scaling
- Configurable WebSocket heartbeat intervals
- Custom authentication backend integration
- Plugin management interface

## Related Documentation

- Django web interface: `src/Server/web/README.md`
- MultiHandler core: `src/Server/Modules/multi_handler/README.md`
- Beacon server: `src/Server/Modules/beacon/beacon_server/`
- Main server: `src/Server/server.py`
