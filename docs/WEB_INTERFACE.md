# PrometheanProxy Web Interface

A modern, real-time web interface for the PrometheanProxy C2 Framework. This web interface provides a user-friendly dashboard for managing beacons, sessions, and commands through your browser.

## Overview

The web interface is built with:
- **Django 5.2** - Web framework
- **Django Channels** - WebSocket support for real-time updates
- **Django REST Framework** - RESTful API
- **Tailwind CSS** - Modern, responsive UI
- **Alpine.js** - Reactive components
- **Redis** - WebSocket message broker

## Features

### 🎯 Real-Time Monitoring
- Live beacon check-ins via WebSockets
- Real-time command execution and output
- Live connection status updates
- Event notifications

### 🎨 Modern UI
- Dark theme optimized for long operations
- Responsive design (desktop, tablet, mobile)
- Interactive dashboard with metrics
- Toast notifications for events

### 🔧 Full Functionality
- Beacon management and monitoring
- Session management with interactive terminals
- Command execution with real-time results
- Command history and filtering
- Connection details and metadata

### 🔐 Security
- Token-based authentication with backend
- Automatic token refresh
- Secure WebSocket connections
- CORS protection

## Quick Start

### Prerequisites

1. **Python 3.12+** with PrometheanProxy installed
2. **Redis Server** for WebSocket support
3. **PrometheanProxy Server** running with multiplayer enabled

### Installation

#### 1. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

#### 2. Install Web Dependencies

From the main PrometheanProxy directory:

```bash
# Activate virtual environment
source venv/bin/activate

# Install web interface dependencies
pip install -r web_requirements.txt
```

This installs:
- Django 5.2
- Django REST Framework
- Django Channels & Daphne
- Redis & Channels-Redis
- CORS Headers
- And other dependencies

#### 3. Configure the Server

Edit `src/Server/config.toml`:

```toml
[multiplayer]
multiplayerEnabled = true
multiplayerListenAddress = "0.0.0.0"
multiplayerPort = 2001
# Web interface settings
webInterface = true        # Enable web interface
webHost = "0.0.0.0"       # Listen on all interfaces
webPort = 8000            # Web interface port
```

#### 4. Start the Server

```bash
# From the main PrometheanProxy directory
python src/Server/server.py
```

The web interface will start automatically if:
- `webInterface = true` in config.toml
- All dependencies are installed
- Redis is running

### Access the Interface

1. Open your browser and navigate to: `http://localhost:8000`
2. Login with your multiplayer server credentials
3. Start managing your C2 infrastructure!

## Configuration

### Environment Variables

The web interface can be configured via environment variables. Create a `.env` file in `src/Server/web/`:

```bash
# Copy example configuration
cd src/Server/web
cp .env.example .env
```

Key settings:

```bash
# Django settings
DEBUG=False                    # Set to False in production
SECRET_KEY=your-secret-key     # Change in production

# Backend API
PROMETHEAN_API_URL=https://localhost:2001
PROMETHEAN_API_VERIFY_SSL=False  # For self-signed certs

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Web server
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
```

### Backend API Configuration

The web interface automatically connects to your multiplayer server based on `config.toml` settings. If you need to override the API URL, set it in the `.env` file.

## Usage

### Dashboard

The main dashboard (`http://localhost:8000`) shows:
- Active beacon count
- Active session count
- Recent beacons
- Activity feed
- System status

### Managing Beacons

1. Click **Beacons** in the sidebar
2. View all active beacons with real-time status
3. Click any beacon for detailed information
4. Execute commands from the beacon detail page
5. Monitor command results in real-time

### Executing Commands

1. Navigate to a beacon detail page
2. Scroll to "Available Commands"
3. Select a command
4. Enter parameters if required
5. Click "Execute"
6. Watch results appear in real-time

### Real-Time Updates

The interface uses WebSockets for live updates:

- **Connected** (green indicator): Receiving real-time updates
- **Disconnected** (red indicator): No WebSocket connection
- **Reconnecting**: Automatically attempting to reconnect

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ├── HTTP/HTTPS ──────┐
       └── WebSocket ───────┤
                            │
    ┌───────────────────────▼──────────────────────┐
    │        Django Web Interface                  │
    │  ┌────────────────────────────────────────┐ │
    │  │  Views & Templates (UI)                │ │
    │  └────────────┬───────────────────────────┘ │
    │               │                              │
    │  ┌────────────▼───────────────────────────┐ │
    │  │  REST API (DRF)                        │ │
    │  │  - Authentication  - Connections       │ │
    │  │  - Commands        - Status            │ │
    │  └────────────┬───────────────────────────┘ │
    │               │                              │
    │  ┌────────────▼───────────────────────────┐ │
    │  │  WebSocket Consumers (Channels)        │ │
    │  │  - Events  - Beacons  - Commands       │ │
    │  └────────────┬───────────────────────────┘ │
    │               │                              │
    │  ┌────────────▼───────────────────────────┐ │
    │  │  API Client Service                    │ │
    │  │  (Proxies to backend)                  │ │
    │  └────────────┬───────────────────────────┘ │
    └───────────────┼──────────────────────────────┘
                    │
                    │ HTTPS
                    │
    ┌───────────────▼──────────────────────────────┐
    │  PrometheanProxy Multiplayer Server          │
    │  (Flask API Backend)                         │
    └──────────────────────────────────────────────┘
```

## API Endpoints

The web interface exposes a RESTful API:

### Authentication
- `POST /api/auth/login/` - Authenticate
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/status/` - Check auth status

### Connections
- `GET /api/connections/` - List beacons/sessions
- `GET /api/connections/details/?uuid=<UUID>` - Connection details

### Commands
- `GET /api/commands/?uuid=<UUID>` - Available commands
- `POST /api/commands/execute/` - Execute command

### WebSocket Endpoints
- `ws://localhost:8000/ws/events/` - Global events
- `ws://localhost:8000/ws/beacons/<uuid>/` - Beacon updates
- `ws://localhost:8000/ws/sessions/<uuid>/` - Session updates
- `ws://localhost:8000/ws/connections/` - Connection monitoring
- `ws://localhost:8000/ws/commands/` - Command monitoring

## Troubleshooting

### "Web interface dependencies missing"

**Solution:**
```bash
source venv/bin/activate
pip install -r web_requirements.txt
```

### "Redis not available"

**Solution:**
```bash
# Start Redis
redis-server --daemonize yes

# Or on Linux with systemd
sudo systemctl start redis
```

### "Backend unreachable"

**Solutions:**
1. Ensure multiplayer server is running and enabled
2. Check firewall settings
3. Verify `PROMETHEAN_API_URL` setting
4. For self-signed certs: `PROMETHEAN_API_VERIFY_SSL=False`

### WebSocket Not Connecting

**Solutions:**
1. Verify Redis is running: `redis-cli ping`
2. Check browser console for errors
3. Ensure no firewall blocking WebSocket connections
4. Check `REDIS_HOST` and `REDIS_PORT` settings

### Port Already in Use

**Solution:**
Change `webPort` in `config.toml`:
```toml
[multiplayer]
webPort = 8080  # Use different port
```

### Login Fails

**Solutions:**
1. Verify credentials work with backend directly
2. Check backend multiplayer server is enabled
3. Check backend logs for authentication errors
4. Ensure user exists in multiplayer database

## Production Deployment

### Using Nginx + Gunicorn + Daphne

For production deployments:

1. **Configure Nginx** to proxy HTTP and WebSocket traffic
2. **Run Gunicorn** for HTTP requests
3. **Run Daphne** for WebSocket connections
4. **Use systemd** for service management

See `src/Server/web/README.md` for detailed production deployment instructions.

### Security Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Use HTTPS (SSL/TLS)
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Enable CSRF protection
- [ ] Use strong passwords
- [ ] Configure firewall rules
- [ ] Regular security updates

## Development

### Project Structure

```
src/Server/web/
├── api/                    # REST API app
│   ├── services.py        # Backend API client
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API endpoints
│   └── urls.py            # API routing
├── c2_interface/          # Web UI app
│   ├── consumers.py       # WebSocket consumers
│   ├── routing.py         # WebSocket routing
│   ├── views.py           # Page views
│   ├── urls.py            # Page routing
│   └── templates/         # HTML templates
├── promethean_web/        # Django project
│   ├── settings.py        # Configuration
│   ├── urls.py            # Main routing
│   └── asgi.py            # ASGI config
├── static/                # Static files
├── manage.py              # Django management
├── .env.example           # Environment template
└── README.md              # Detailed documentation
```

### Running Manually

If you want to run the web interface independently:

```bash
cd src/Server/web

# Run migrations
python manage.py migrate

# Start with Daphne (WebSocket support)
daphne -b 0.0.0.0 -p 8000 promethean_web.asgi:application

# Or use Django dev server (limited WebSocket support)
python manage.py runserver 0.0.0.0:8000
```

### Adding Features

See `src/Server/web/README.md` for detailed development documentation including:
- Adding API endpoints
- Creating WebSocket consumers
- Adding new pages
- Customizing the UI
- Extending functionality

## Documentation

- **Full Web Interface Docs**: `src/Server/web/README.md`
- **Quick Start Guide**: `src/Server/web/QUICKSTART.md`
- **API Documentation**: Available at `/api/` when running
- **Main PrometheanProxy Docs**: `README.md`

## Integration with PrometheanProxy

The web interface is fully integrated with the PrometheanProxy server:

1. **Automatic Startup**: Starts with the server when `webInterface = true`
2. **Shared Authentication**: Uses multiplayer server credentials
3. **Real-time Sync**: Direct API communication with backend
4. **Thread-based**: Runs in a separate thread alongside the server
5. **No Interference**: Server continues to work if web interface fails

## Support

For issues, questions, or contributions:
- Check the troubleshooting section above
- Review `src/Server/web/README.md` for detailed docs
- Check existing GitHub issues
- Open a new issue with detailed information

## Future Enhancements

Planned features:
- [ ] Interactive beacon map with geolocation
- [ ] File upload/download interface
- [ ] Advanced command templating
- [ ] Multi-user real-time collaboration
- [ ] Audit logging and reporting
- [ ] Beacon grouping and tagging
- [ ] Scheduled command execution
- [ ] Custom dashboard widgets
- [ ] Mobile app integration
- [ ] Advanced analytics and metrics

## License

See the main PrometheanProxy LICENSE file.

---

**For authorized testing and research use only. Requires explicit permission from all parties.**