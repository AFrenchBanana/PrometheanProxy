# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrometheanProxy is a modular C2 framework for authorized testing. Go-based implant (Linux/Windows) with Python server, featuring runtime-pluggable commands and obfuscated wire protocol.

## Common Commands

```bash
# Setup
make venv                    # Create Python venv and install deps

# Build
make build                   # Full build (linux + windows + plugins)
make linux                   # Go implant (release + debug) for Linux
make windows                 # Go implant (release + debug) for Windows
make plugins                 # Compile all Go plugins (auto-discovered)
make server                  # PyInstaller ELF with embedded plugins

# Install plugins for source runs
make install-all-plugins     # Stage to ~/.PrometheanProxy/plugins/

# Run
PYTHONPATH=src python3 src/Server/server.py    # Server from source
make run-client                                 # Client debug mode

# Test & Lint
make test                    # Python unit tests
make lint                    # flake8 (max line 150)

# Maintenance
make clean                   # Remove build artifacts
make dependency-update       # Update Go deps (client + plugins)
```

## Architecture

### Client (Go) - `src/Client/`
- **Entry**: `main.go` - dual connection modes (beacon/session)
- **beacon/**: HTTP beaconing with URL obfuscation (`http/urlObfuscation.go`)
- **session/**: Persistent TCP/TLS for interactive commands
- **generic/config/**: Config loading, obfuscation mapping, build tag handling (`config_debug.go` vs `config_nodebug.go`)
- **generic/rpc_client/**: HashiCorp go-plugin RPC with lazy-start (plugins spawned on-demand)
- **generic/commands/**: Built-in commands (shell, directory traversal)
- **dynamic/shared/**: Plugin RPC interface definition

### Server (Python) - `src/Server/`
- **Entry**: `server.py` - startup, asset extraction from PyInstaller bundle
- **Modules/beacon/**: Flask HTTP server, command queueing
- **Modules/session/**: Persistent connections, file transfer
- **Modules/multi_handler/**: Main CLI, beacon/session management
- **ServerDatabase/**: SQLite abstraction
- **Plugins/**: Go and Python plugins (template at `Plugins/template/`)

### Key Files
- `src/Server/config.toml` - Server config (copied to `~/.PrometheanProxy/` on first run)
- `src/Server/obfuscate.json` - JSON field obfuscation map (shared with client via ldflags)
- `~/.PrometheanProxy/Certificates/hmac.key` - HMAC key (optional, read by Makefile)

## Build System

**Debug vs Release**:
- Release: `-ldflags="-s -w"` (stripped)
- Debug: `-tags=debug` (verbose logging, no output suppression)

**Plugin auto-discovery**: Makefile finds all `Plugins/*/main.go` (excluding template) and generates build rules for Linux/Windows release/debug variants.

**Ldflags injection**: HMAC key and obfuscation config path injected at compile time.

## Plugin Development

Use `src/Server/Plugins/template/` as starting point:
- Go plugins: `main.go` implementing RPC interface from `src/Client/dynamic/shared/`
- Python plugins: `.py` file with same interface
- Per-plugin `obfuscate.json` for wire-level name obfuscation

Plugins output to `Plugins/<name>/{release,debug}/` as `.so` (Linux) or `.dll` (Windows).
