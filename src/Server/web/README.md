# PrometheanProxy Web Interface

A modern, real-time web interface for the PrometheanProxy C2 Framework built with Django, Django Channels, and Tailwind CSS.

![PrometheanProxy Web Interface](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Django](https://img.shields.io/badge/django-5.2-green.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![WebSockets](https://img.shields.io/badge/websockets-enabled-orange.svg)

## Features

### 🎯 Real-Time Monitoring
- **Live Event Stream**: Real-time updates via WebSockets for beacon check-ins, command execution, and system events
- **Interactive Dashboard**: Overview of all beacons, sessions, and system metrics
- **Connection Monitoring**: Track all active beacons and sessions with live status updates

### 🎨 Modern UI/UX
- **Tailwind CSS**: Beautiful, responsive design that works on all devices
- **Dark Theme**: Easy on the eyes for long operations
- **Alpine.js**: Reactive components without the complexity
- **Real-time Notifications**: Toast notifications for important events

### 🔧 Comprehensive Functionality
- **Beacon Management**: View, monitor, and interact with all beacons
- **Session Management**: Interactive terminal sessions with implants
- **Command Execution**: Execute commands and view results in real-time
- **Command History**: Track all executed commands and their outputs
- **Search & Filtering**: Quickly find specific beacons or sessions

### 🔐 Security
- **Token-based Authentication**: Secure JWT authentication with the backend
- **Session Management**: Automatic token refresh and expiration handling
- **SSL/TLS Support**: Full HTTPS support for production deployments
- **CORS Protection**: Configurable CORS policies

### 🚀 Performance
- **Async/Await**: Fully asynchronous for maximum performance
- **WebSocket Support**: Efficient real-time communication via Django Channels
- **Redis Caching**: Fast message delivery through Redis channel layers
- **Optimized Queries**: Efficient data loading and pagination

## Architecture

```
┌─────────────────────┐
│   Web Browser       │
│  (Frontend/HTML)    │
└──────────┬──────────┘
           │
           ├─── HTTP/HTTPS ────┐
           │                   │
           └─── WebSocket ─────┤
                               │
┌──────────────────────────────▼────────────────────────────┐
│                Django Web Application                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Django Views & Templates              │  │
│  └─────────────────────┬──────────────────────────────┘  │
│                        │                                   │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │           REST API (Django REST Framework)        │  │
│  │  - Authentication    - Connections                │  │
│  │  - Commands          - Status                     │  │
│  └────────────────────┬──────────────────────────────┘  │
│                       │                                   │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │         WebSocket Consumers (Channels)            │  │
│  │  - Events Stream     - Beacon Monitor             │  │
│  │  - Command Monitor   - Session Monitor            │  │
│  └────────────────────┬──────────────────────────────┘  │
│                       │                                   │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │           API Client Service Layer                │  │
│  │    (Communicates with PrometheanProxy Backend)    │  │
│  └────────────────────┬──────────────────────────────┘  │
└───────────────────────┼────────────────────────────────┘
                        │
                        │ HTTPS/API
                        │
┌───────────────────────▼────────────────────────────────┐
│         PrometheanProxy Multiplayer Server             │
│              (Flask-based API Backend)                 │
│  - Beacon Management    - Session Management           │
│  - Command Queueing     - Authentication               │
└────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.12+
- Redis Server (for WebSocket support)
- PrometheanProxy C2 server running with multiplayer server enabled

### Quick Start

1. **Install Redis** (if not already installed):

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

2. **Install Python Dependencies**:

```bash
cd web
pip install -r ../web_requirements.txt
```

3. **Configure Environment**:

```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

Key settings to configure:
- `PROMETHEAN_API_URL`: URL of your PrometheanProxy multiplayer server (default: https://localhost:8443)
- `PROMETHEAN_API_VERIFY_SSL`: Set to False for self-signed certificates in development
- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)

4. **Run Database Migrations**:

```bash
python manage.py migrate
```

5. **Create Superuser (Optional)**:

```bash
python manage.py createsuperuser
```

6. **Collect Static Files** (for production):

```bash
python manage.py collectstatic --noinput
```

7. **Run Development Server**:

```bash
# Development mode (HTTP)
python manage.py runserver 0.0.0.0:8000

# With Channels support (WebSockets)
daphne -b 0.0.0.0 -p 8000 promethean_web.asgi:application
```

8. **Access the Interface**:

Open your browser and navigate to: `http://localhost:8000`

## Usage

### Authentication

1. Navigate to the login page at `http://localhost:8000/login/`
2. Enter your PrometheanProxy backend credentials
3. Click "Sign In"

The web interface authenticates directly with the PrometheanProxy multiplayer server. Use the same credentials you configured for the backend.

### Dashboard

The dashboard provides an at-a-glance view of your C2 infrastructure:
- Active beacon count
- Active session count
- Recent activity feed
- Quick actions

### Managing Beacons

**Viewing Beacons:**
- Navigate to "Beacons" in the sidebar
- See all active beacons with real-time status
- Filter and search beacons

**Beacon Details:**
- Click on any beacon to view detailed information
- See beacon metadata (hostname, OS, IP address)
- View beacon check-in history
- Execute commands on the beacon

### Managing Sessions

**Viewing Sessions:**
- Navigate to "Sessions" in the sidebar
- See all active interactive sessions

**Interactive Session:**
- Click on a session to open the interactive terminal
- Execute commands in real-time
- View session output and history

### Executing Commands

**Via Beacon Detail Page:**
1. Navigate to a beacon's detail page
2. Select a command from the available commands list
3. Enter any required parameters
4. Click "Execute"
5. View results in real-time via WebSocket updates

**Via Commands Page:**
- Navigate to "Commands" in the sidebar
- View command history across all beacons
- Filter by beacon, command type, or status

### Real-Time Updates

The interface uses WebSockets for real-time updates:
- **Event Stream**: Global events (new beacons, disconnections)
- **Beacon Monitor**: Per-beacon updates (check-ins, command results)
- **Session Monitor**: Per-session updates (I/O, status changes)
- **Command Monitor**: Command execution status and output

Connection status is shown in the top bar and updates automatically.

## API Endpoints

The web interface provides a RESTful API that proxies requests to the PrometheanProxy backend:

### Authentication
- `POST /api/auth/login/` - Authenticate with backend
- `POST /api/auth/logout/` - Logout and invalidate token
- `GET /api/auth/status/` - Check authentication status

### Connections
- `GET /api/connections/` - List all beacons and sessions
- `GET /api/connections/details/?uuid=<UUID>` - Get connection details
- `GET /api/connections/details/?uuid=<UUID>&commands` - Include command history

### Commands
- `GET /api/commands/?uuid=<UUID>` - Get available commands for a connection
- `POST /api/commands/execute/` - Execute a command

### Health Checks
- `GET /api/health/` - Check web interface health
- `GET /api/health/backend/` - Check backend connectivity

### WebSocket Endpoints

- `ws://localhost:8000/ws/events/` - Global event stream
- `ws://localhost:8000/ws/beacons/<uuid>/` - Beacon-specific updates
- `ws://localhost:8000/ws/sessions/<uuid>/` - Session-specific updates
- `ws://localhost:8000/ws/connections/` - All connections monitor
- `ws://localhost:8000/ws/commands/` - Command execution monitor

## Development

### Project Structure

```
web/
├── api/                          # REST API application
│   ├── services.py              # Backend API client service
│   ├── serializers.py           # DRF serializers
│   ├── views.py                 # API view endpoints
│   └── urls.py                  # API URL routing
├── c2_interface/                # Web UI application
│   ├── consumers.py             # WebSocket consumers
│   ├── routing.py               # WebSocket URL routing
│   ├── views.py                 # Page views
│   ├── urls.py                  # Page URL routing
│   └── templates/               # HTML templates
│       └── c2_interface/
│           ├── base.html        # Base template
│           ├── dashboard.html   # Dashboard page
│           ├── login.html       # Login page
│           └── ...              # Other pages
├── promethean_web/              # Django project settings
│   ├── settings.py              # Django configuration
│   ├── urls.py                  # Main URL routing
│   ├── asgi.py                  # ASGI config (WebSockets)
│   └── wsgi.py                  # WSGI config (HTTP)
├── static/                      # Static files (CSS, JS, images)
├── manage.py                    # Django management script
├── .env.example                 # Environment configuration example
└── README.md                    # This file
```

### Adding New Features

#### 1. Adding a New API Endpoint

**Create the serializer** (`api/serializers.py`):
```python
class MyNewSerializer(serializers.Serializer):
    field1 = serializers.CharField()
    field2 = serializers.IntegerField()
```

**Create the view** (`api/views.py`):
```python
class MyNewView(APIView):
    def get(self, request):
        # Your logic here
        return Response(data, status=status.HTTP_200_OK)
```

**Add the URL** (`api/urls.py`):
```python
path('mynew/', MyNewView.as_view(), name='my_new_endpoint'),
```

#### 2. Adding a New WebSocket Consumer

**Create the consumer** (`c2_interface/consumers.py`):
```python
class MyNewConsumer(BaseConsumer):
    async def connect(self):
        self.room_group_name = "my_new_group"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await super().connect()
    
    async def my_event(self, event):
        await self.send_message("my_event", event.get("data"))
```

**Add the route** (`c2_interface/routing.py`):
```python
path("ws/mynew/", consumers.MyNewConsumer.as_asgi(), name="ws_mynew"),
```

#### 3. Adding a New Page

**Create the view** (`c2_interface/views.py`):
```python
class MyNewPageView(TemplateView):
    template_name = "c2_interface/mynewpage.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "My New Page"
        context["active_page"] = "mynew"
        return context
```

**Create the template** (`c2_interface/templates/c2_interface/mynewpage.html`):
```html
{% extends "c2_interface/base.html" %}

{% block content %}
<div>
    <h1>My New Page</h1>
    <!-- Your content here -->
</div>
{% endblock %}
```

**Add the URL** (`c2_interface/urls.py`):
```python
path("mynew/", views.MyNewPageView.as_view(), name="mynew"),
```

### Backend API Service

The `api/services.py` module provides a clean interface to the PrometheanProxy backend:

```python
from api.services import get_api_client

# Get the shared client instance
client = get_api_client()

# Login
client.login("username", "password")

# Get connections
connections = client.get_connections()

# Execute command
result = client.execute_command(uuid="...", command="whoami")

# Logout
client.logout()
```

The service handles:
- Authentication and token management
- Automatic token refresh
- SSL/TLS verification (configurable)
- Request retry logic
- Error handling and exceptions

### Sending WebSocket Events

To send events to connected WebSocket clients from your code:

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

# Send to a specific group
async_to_sync(channel_layer.group_send)(
    "c2_events",  # Group name
    {
        "type": "beacon_event",  # Handler method name (snake_case)
        "data": {
            "event": "new_beacon",
            "uuid": "beacon-uuid-here",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
)
```

## Production Deployment

### Using Gunicorn + Daphne

For production, use Gunicorn for HTTP and Daphne for WebSocket connections:

```bash
# Install production dependencies
pip install gunicorn

# Run Daphne (WebSockets) on port 8001
daphne -b 0.0.0.0 -p 8001 promethean_web.asgi:application

# Run Gunicorn (HTTP) on port 8000
gunicorn promethean_web.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Nginx Configuration

Example Nginx configuration:

```nginx
upstream django_http {
    server 127.0.0.1:8000;
}

upstream django_ws {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Static files
    location /static/ {
        alias /path/to/web/staticfiles/;
    }

    location /media/ {
        alias /path/to/web/media/;
    }

    # WebSocket connections
    location /ws/ {
        proxy_pass http://django_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # HTTP requests
    location / {
        proxy_pass http://django_http;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service Files

**daphne.service:**
```ini
[Unit]
Description=Daphne (Django Channels)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/web
ExecStart=/path/to/venv/bin/daphne -b 0.0.0.0 -p 8001 promethean_web.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**gunicorn.service:**
```ini
[Unit]
Description=Gunicorn (Django WSGI)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/web
ExecStart=/path/to/venv/bin/gunicorn promethean_web.wsgi:application --bind 0.0.0.0:8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable daphne gunicorn
sudo systemctl start daphne gunicorn
```

## Troubleshooting

### WebSocket Connection Issues

**Problem**: WebSockets not connecting

**Solutions**:
- Ensure Redis is running: `redis-cli ping` (should return `PONG`)
- Check WebSocket URL in browser console
- Verify firewall allows WebSocket connections
- Check Nginx/proxy WebSocket configuration

### Backend Connection Issues

**Problem**: "Backend unreachable" error

**Solutions**:
- Verify PrometheanProxy multiplayer server is running
- Check `PROMETHEAN_API_URL` in `.env` file
- If using self-signed certificates, set `PROMETHEAN_API_VERIFY_SSL=False`
- Check network connectivity to backend server

### Authentication Issues

**Problem**: Login fails with valid credentials

**Solutions**:
- Verify credentials work with backend directly
- Check backend logs for authentication errors
- Ensure backend multiplayer server is properly configured
- Clear browser cache and localStorage

### Static Files Not Loading

**Problem**: CSS/JS not loading in production

**Solutions**:
```bash
python manage.py collectstatic --noinput
```
- Verify `STATIC_ROOT` and `STATIC_URL` settings
- Check Nginx static file configuration
- Ensure correct file permissions

## Performance Optimization

### Redis Configuration

For better performance, tune Redis settings:

```bash
# /etc/redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Database Optimization

For large deployments, use PostgreSQL instead of SQLite:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'promethean_web',
        'USER': 'promethean',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Caching

Enable caching for better performance:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

## License

See the main PrometheanProxy LICENSE file.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section above

## Roadmap

Planned features:
- [ ] Interactive beacon map with geographic visualization
- [ ] File upload/download interface
- [ ] Advanced command templating
- [ ] Multi-user collaboration features
- [ ] Audit logging and reporting
- [ ] Beacon grouping and tagging
- [ ] Scheduled command execution
- [ ] Custom dashboard widgets
- [ ] Mobile-responsive improvements
- [ ] Dark/light theme toggle

---

**For authorized testing and research use only. Requires explicit permission.**