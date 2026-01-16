# PrometheanProxy Web Interface - Quick Start Guide

Get the web interface up and running in 5 minutes!

## Prerequisites

Before you begin, ensure you have:
- ✅ Python 3.12+ installed
- ✅ Redis server installed
- ✅ PrometheanProxy C2 server running with multiplayer enabled

## Installation

### 1. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### 2. Install Python Dependencies

```bash
cd web
pip install -r ../web_requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:
```bash
# Minimum required settings:
PROMETHEAN_API_URL=https://localhost:8443
PROMETHEAN_API_VERIFY_SSL=False  # For self-signed certificates
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4. Initialize Database

```bash
python manage.py migrate
```

### 5. Start the Server

**Option A: Using the startup script (recommended)**
```bash
./start_web.sh
```

**Option B: Manual start**
```bash
daphne -b 0.0.0.0 -p 8000 promethean_web.asgi:application
```

### 6. Access the Interface

Open your browser and navigate to:
```
http://localhost:8000/login/
```

## First Login

1. Navigate to `http://localhost:8000/login/`
2. Enter your PrometheanProxy backend credentials
   - **Username:** Your multiplayer server username
   - **Password:** Your multiplayer server password
3. Click "Sign In"
4. You'll be redirected to the dashboard

## Quick Tour

### Dashboard (`/`)
- Overview of all active beacons and sessions
- Real-time statistics
- Recent activity feed
- Quick actions

### Beacons (`/beacons/`)
- List all active beacons
- View beacon details
- Execute commands on beacons
- Monitor beacon status

### Sessions (`/sessions/`)
- List all active sessions
- Interactive terminal sessions
- Real-time session I/O

### Commands (`/commands/`)
- Command history across all connections
- Filter and search commands
- View command results

## Real-Time Features

The interface uses **WebSockets** for real-time updates:

- 🟢 **Live beacon status** - See beacons check in as it happens
- 🔵 **Command execution** - Watch command output stream in real-time
- 🟡 **Event notifications** - Get notified of important events
- 🟣 **Connection monitoring** - Track connections and disconnections

Look for the connection status indicator in the top bar:
- 🟢 **Connected** - WebSocket is active
- 🔴 **Disconnected** - WebSocket connection lost (will auto-reconnect)

## Common Tasks

### Execute a Command on a Beacon

1. Go to **Beacons** page
2. Click on a beacon to view details
3. Scroll to "Available Commands"
4. Select a command
5. Enter any required parameters
6. Click "Execute"
7. Watch the output appear in real-time

### Monitor a Specific Beacon

1. Navigate to the beacon detail page (`/beacons/<uuid>/`)
2. The page automatically connects to a WebSocket for real-time updates
3. You'll see:
   - Check-in events
   - Command executions
   - Status changes

### View Command History

1. Go to **Commands** page
2. See all executed commands across all beacons
3. Filter by beacon UUID, command name, or status
4. Click on any command to see full details and output

## Troubleshooting

### "Backend unreachable" Error

**Problem:** Cannot connect to PrometheanProxy server

**Solutions:**
1. Verify the multiplayer server is running:
   ```bash
   # In the main PrometheanProxy directory
   python src/Server/server.py
   ```
2. Check the `PROMETHEAN_API_URL` in `.env`
3. If using self-signed certificates, set `PROMETHEAN_API_VERIFY_SSL=False`
4. Check firewall settings

### WebSocket Not Connecting

**Problem:** Real-time updates not working

**Solutions:**
1. Verify Redis is running:
   ```bash
   redis-cli ping
   ```
2. Check browser console for WebSocket errors
3. Ensure `REDIS_HOST` and `REDIS_PORT` are correct in `.env`
4. Try restarting the web server

### Login Fails with Valid Credentials

**Problem:** "Authentication failed" error

**Solutions:**
1. Verify credentials work with the backend directly
2. Check backend logs for authentication errors
3. Ensure multiplayer server is enabled in backend config
4. Try accessing backend health endpoint:
   ```bash
   curl -k https://localhost:8443/ping
   ```

### Static Files Not Loading

**Problem:** CSS/JS not loading

**Solutions:**
```bash
python manage.py collectstatic --noinput
```

### Port Already in Use

**Problem:** "Address already in use" error

**Solutions:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or use a different port
daphne -b 0.0.0.0 -p 8080 promethean_web.asgi:application
```

## Development Tips

### Enable Debug Mode

In `.env`:
```bash
DEBUG=True
```

**Note:** Never use `DEBUG=True` in production!

### View Django Admin

1. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

2. Access admin at: `http://localhost:8000/admin/`

### Check Backend Status

```bash
curl http://localhost:8000/api/health/backend/
```

### View Logs

**Application logs:**
```bash
tail -f logs/django.log
```

**Redis logs:**
```bash
# Ubuntu/Debian
tail -f /var/log/redis/redis-server.log

# macOS
tail -f /usr/local/var/log/redis.log
```

## Production Deployment

For production deployments, see the full [README.md](README.md#production-deployment) for:
- Nginx configuration
- Gunicorn + Daphne setup
- SSL/TLS configuration
- Systemd service files
- Performance optimization

## Quick Commands Reference

```bash
# Start development server
./start_web.sh

# Check dependencies
./start_web.sh --check

# Run migrations
./start_web.sh --migrate
python manage.py migrate

# Collect static files
./start_web.sh --static
python manage.py collectstatic

# Create superuser
python manage.py createsuperuser

# Start Redis
redis-server --daemonize yes

# Check Redis status
redis-cli ping

# View logs
tail -f logs/django.log

# Run Django shell
python manage.py shell

# Start production servers
./start_web.sh --production
```

## Next Steps

Now that you're up and running:

1. 📖 Read the full [README.md](README.md) for advanced features
2. 🔧 Customize settings in `.env` for your environment
3. 🎨 Explore the dashboard and all features
4. 📊 Monitor your C2 infrastructure in real-time
5. 🚀 Deploy to production when ready

## Getting Help

- 📚 **Full Documentation:** [README.md](README.md)
- 🐛 **Issues:** Open an issue on GitHub
- 💡 **Troubleshooting:** See the troubleshooting section above
- 🔒 **Security:** This is for authorized use only

---

**Happy hunting! 🔥**

For authorized testing and research use only. Requires explicit permission.