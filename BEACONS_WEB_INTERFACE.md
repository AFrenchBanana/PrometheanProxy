# Beacon Web Interface

## Overview

This document describes the new beacon management features added to the PrometheanProxy web interface. These features allow you to view, manage, and interact with beacons through a modern web UI, with full command execution capabilities using the same command modules available in the CLI multihandler.

## Features Added

### 1. Beacons API Endpoint (`/api/beacons/`)

A new REST API endpoint that returns only beacon connections (filtering out sessions).

**Endpoint:** `GET /api/beacons/`

**Authentication:** Required (Bearer token)

**Response:**
```json
{
  "beacons": [
    {
      "userID": "string",
      "uuid": "string",
      "address": "string",
      "hostname": "string",
      "operating_system": "string",
      "last_beacon": "string",
      "next_beacon": "string",
      "timer": float,
      "jitter": float,
      "loaded_modules": ["string"]
    }
  ]
}
```

### 2. Beacons List Page (`/beacons/`)

A comprehensive beacon management dashboard with:

- **Real-time Statistics:**
  - Total beacon count
  - Active beacons (checked in within 5 minutes)
  - Idle beacons (5 minutes to 1 hour)
  - Lost beacons (no check-in for over 1 hour)

- **Filtering & Search:**
  - Search by UUID, hostname, IP address, or OS
  - Filter by operating system (Windows, Linux, MacOS, Android)
  - Filter by status (active, idle, lost)

- **Beacon Information Display:**
  - Status indicator (color-coded)
  - UUID (shortened with full on hover)
  - Hostname
  - IP Address
  - Operating System (with icons)
  - Last seen timestamp (absolute and relative)
  - Check-in timer and jitter percentage

- **Quick Actions:**
  - Interact button (opens beacon detail page)
  - Delete button (queues shutdown command)
  - Auto-refresh every 5 seconds

### 3. Beacon Detail Page (`/beacons/<uuid>/`)

An interactive command execution interface for individual beacons:

#### Beacon Information Panel
- Full UUID with copy-to-clipboard
- Hostname, IP address, OS
- Last seen and next expected check-in times
- Check-in timer/jitter configuration
- Loaded modules list
- Real-time status indicator

#### Command Execution Interface

**Available Commands Panel:**
- Searchable list of all available commands
- Commands loaded from multihandler plugins
- Click to select command for execution

**Command Execution Panel:**
- Command input (type or select from list)
- Optional arguments field (supports JSON or plain text)
- Execute button with status feedback
- Command history with timestamps and status
- Output display area

**Quick Actions:**
- Pre-configured buttons for common commands:
  - `whoami` - Get current user
  - `pwd` - Get current directory
  - `sysinfo` - Get system information
  - `session` - Switch to interactive session mode
  - `shutdown` - Gracefully shutdown beacon

#### Queued Commands View
- Table of all queued commands for the beacon
- Command UUID, status (pending/completed)
- Command output when available
- Refresh button for manual updates

### 4. Enhanced Backend Support

#### Multihandler Command Integration

The web interface now uses the same command modules as the CLI multihandler:

```python
# Commands are loaded from multihandler plugins
handler = MultiHandlerCommands(config, None)
beacon_commands = handler.list_loaded_beacon_commands()
```

**Built-in Commands:**
- `shell` - Execute shell commands
- `close` - Close beacon connection
- `session` - Switch to session mode
- `shutdown` - Shutdown beacon
- `sysinfo` - Get system information

**Plugin Commands:**
All beacon plugins from the `Plugins/` directory are automatically discovered and made available.

#### Updated API Handlers

**Commands Handler Updates:**
- `_get_multihandler_commands()` - Retrieves available commands from plugins
- Returns actual plugin commands instead of hardcoded test commands
- Falls back to basic commands if multihandler unavailable

**Connections Handler Updates:**
- Added `loaded_modules` field to beacon connection info
- Provides module information for both list and detail endpoints

## Usage

### Accessing the Beacon Interface

1. Start the PrometheanProxy server with web interface enabled:
   ```bash
   # In config.toml
   [multiplayer]
   webInterface = true
   webHost = "0.0.0.0"
   webPort = 8000
   ```

2. Navigate to `http://localhost:8000/beacons/`

3. Log in with your multiplayer server credentials

### Viewing Beacons

The beacons list page automatically refreshes every 5 seconds and displays:
- Color-coded status indicators (green=active, yellow=idle, red=lost)
- Real-time statistics in dashboard cards
- Sortable and filterable beacon table

### Executing Commands

1. Click "Interact" on any beacon in the list
2. Select a command from the available commands panel, or type it manually
3. (Optional) Add command arguments in JSON or plain text format
4. Click "Execute" to queue the command
5. The command will be executed on the beacon's next check-in
6. Monitor the "Queued Commands" section for status and output

### Command Examples

**Execute shell command:**
```
Command: shell
Arguments: whoami
```

**Load a module:**
```
Command: load_module
Arguments: {"module": "screenshot"}
```

**Switch to session mode:**
```
Command: session
Arguments: (none)
```

## Architecture

### Frontend Stack
- **Tailwind CSS** - Utility-first CSS framework
- **Alpine.js** - Reactive JavaScript framework
- **Font Awesome** - Icon library

### Backend Stack
- **Django REST Framework** - API endpoints
- **Flask** (Multiplayer Server) - Backend API
- **PrometheanProxy** - Core C2 functionality

### Data Flow

```
Web UI → Django API → Multiplayer Server → Beacon Registry
                ↓
        Queue Command
                ↓
    Beacon checks in → Execute command → Store output
                ↓
        Web UI polls for updates
```

## Security Considerations

1. **Authentication Required:** All beacon operations require valid authentication token
2. **Command Validation:** Commands are validated against available plugin list
3. **Authorization:** Token-based authorization for all API calls
4. **SSL/TLS:** Web interface should be served over HTTPS in production

## Troubleshooting

### Beacons not appearing
- Verify beacon is checking in (check server logs)
- Ensure beacon is properly registered in `beacon_list`
- Check database connection settings

### Commands not executing
- Verify command is in the available commands list
- Check that the beacon has loaded required modules
- Review beacon command queue in database
- Check server logs for errors

### Web interface not loading
- Verify web interface is enabled in config.toml
- Check that Django dependencies are installed
- Ensure Redis is running (for WebSocket support)
- Check web server logs: `src/Server/web/logs/`

## API Reference

### GET /api/beacons/
Returns list of all beacons.

**Headers:**
- `Authorization: Bearer <token>`

**Response:** 200 OK
```json
{
  "beacons": [...]
}
```

### GET /api/connections/details?uuid=<uuid>
Returns detailed information about a specific beacon.

**Query Parameters:**
- `uuid` (required) - Beacon UUID
- `commands` (optional) - Include command history if present

### GET /api/commands?uuid=<uuid>
Returns available commands for a beacon.

**Query Parameters:**
- `uuid` (required) - Beacon UUID

### POST /api/commands/execute/
Execute a command on a beacon.

**Body:**
```json
{
  "uuid": "beacon-uuid",
  "command": "command-name",
  "data": "optional-arguments"
}
```

## Development

### Adding New Commands

Commands are automatically discovered from the `Plugins/` directory. To add a new beacon command:

1. Create a plugin in `src/Server/Plugins/your_command/`
2. Implement the `beacon()` method
3. Set the `command` attribute
4. Plugin will be automatically loaded and appear in web interface

Example:
```python
class YourCommand:
    command = "your_command"
    
    def beacon(self, beacon):
        # Queue command for beacon
        from Modules.beacon.beacon import add_beacon_command_list
        add_beacon_command_list(
            beacon.userID, 
            None, 
            self.command,
            beacon.database,
            {"args": "your_args"}
        )
```

### Frontend Customization

Templates are located in:
- `src/Server/web/c2_interface/templates/c2_interface/beacons_list.html`
- `src/Server/web/c2_interface/templates/c2_interface/beacon_detail.html`

Modify these files to customize the UI, add new features, or change layouts.

## Future Enhancements

Potential improvements for future versions:

- [ ] Real-time command output via WebSockets
- [ ] Bulk command execution across multiple beacons
- [ ] Command templates and macros
- [ ] Beacon grouping and tagging
- [ ] Export beacon data to CSV/JSON
- [ ] Advanced filtering (by date range, modules, etc.)
- [ ] Command scheduling (execute at specific time)
- [ ] Beacon analytics and metrics dashboard
- [ ] Interactive terminal emulator for sessions
- [ ] File browser and download interface

## Contributing

When adding features to the beacon web interface:

1. Follow existing code patterns and style
2. Add appropriate error handling
3. Update this documentation
4. Test with multiple beacon types (Windows, Linux, etc.)
5. Verify command execution works correctly
6. Ensure mobile responsiveness

## License

Same as PrometheanProxy main project.