# PrometheanProxy C2
```text   ___                          _   _                        ___                     
   / _ \_ __ ___  _ __ ___   ___| |_| |__   ___  __ _ _ __   / _ \_ __ _____  ___   _ 
 / /_)/ '__/ _ \| '_ ` _ \ / _ \ __| '_ \ / _ \/ _` | '_ \ / /_)/ '__/ _ \ \/ / | | |
/ ___/| | | (_) | | | | | |  __/ |_| | | |  __/ (_| | | | / ___/| | | (_) >  <| |_| |
\/    |_|  \___/|_| |_| |_|\___|\__|_| |_|\___|\__,_|_| |_|\/    |_|  \___/_/\_\\__, |
                                                                                                                      |___/ 
```
[contributors-shield]: https://img.shields.io/github/contributors/AFrenchBanana/PrometheanProxy.svg?style=for-the-badge
[contributors-url]: https://github.com/AFrenchBanana/PrometheanProxy/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/AFrenchBanana/PrometheanProxy.svg?style=for-the-badge
[forks-url]: https://github.com/AFrenchBanana/PrometheanProxy/network/members
[stars-shield]: https://img.shields.io/github/stars/AFrenchBanana/PrometheanProxy.svg?style=for-the-badge
[stars-url]: https://github.com/AFrenchBanana/PrometheanProxy/stargazers
[issues-shield]: https://img.shields.io/github/issues/AFrenchBanana/PrometheanProxy.svg?style=for-the-badge
[issues-url]: https://github.com/AFrenchBanana/PrometheanProxy/issues
[license-shield]: https://img.shields.io/github/license/AFrenchBanana/PrometheanProxy.svg?style=for-the-badge
[license-url]: https://github.com/AFrenchBanana/PrometheanProxy/blob/master/LICENSE


[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicense License][license-shield]][license-url]



## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Future Features](#future-features)
- [Disclaimer](#disclaimer)

## Overview
PrometheanProxy is a modular command-and-control framework with a Go-based implant and a Python-based server. It focuses on runtime-pluggable command modules and an obfuscated wire format that can be adjusted without recompiling. Some components (like the remote management client) are actively in progress.

## Features
- Go implant (Linux/Windows) with beaconing and session modes
- Python server with:
   - Beacon HTTP endpoint and command queueing
   - Multi-handler architecture for sessions and utilities
   - SQLite-backed server database
   - Packet sniffer utility (optional)
- Dynamic, plugin-delivered commands:
   - Go plugin binaries are built per-plugin and delivered to implants at runtime
   - Plugins implement a stable RPC interface and are executed on-demand (lazy start)
- Obfuscated protocol surface:
   - JSON key obfuscation for request/response fields via `obfuscate.json`
   - Obfuscation of module/plugin names (per-plugin `obfuscate.json` supported)
   - Randomized, web-like URL paths/params for beaconing endpoints
- Build tooling:
   - Make targets to build the Go implant and the Python server (PyInstaller ELF)
   - Automatic discovery and compilation of Go-based plugins
   - Install helpers to stage plugins under `~/.PrometheanProxy/plugins`

## Architecture
### Client (Go)
- Beaconing over plain HTTP (configurable host/port) with randomized URL paths; see `src/Client/beacon/http/urlObfuscation.go`
- Obfuscated JSON fields defined by `src/Server/obfuscate.json` and mapped in `src/Client/generic/config/obfuscation_map.go`
- Dynamic command loading via HashiCorp go-plugin RPC; see `src/Client/dynamic/shared/` and `src/Client/generic/rpc_client/`
- Built-in commands and a session shell are available; new commands are first-class plugins

### Server (Python)
- Beacon HTTP server (no TLS by default) defined in `Modules/beacon/beacon_server`
- Command queueing and dispatch for beacons in `Modules/beacon/beacon.py`
- Unified plugin model:
   - Compiled Go plugins live under `~/.PrometheanProxy/plugins/<name>/{release,debug}/`
   - Python plugin sources are available under `~/.PrometheanProxy/plugins/Plugins/...`
   - Module loading sends base64-encoded plugin binaries to the implant, using obfuscated module names
- Configuration and logging loaded from `~/.PrometheanProxy/config.toml` (auto-copied on first run)

## Prerequisites
- Go 1.20+ (tested on Linux/Windows amd64)
- Python 3.12 (server), pip/venv
- make, gcc/clang toolchain for building Go and packaging the server

## Installation
1) Clone and set up a virtualenv for the server

```bash
git clone https://github.com/AFrenchBanana/PrometheanProxy.git
cd PrometheanProxy
make venv
```

2) Build server (PyInstaller ELF) and Go plugins (optional but recommended)

```bash
make server       # builds bin/PrometheanProxy
make plugins      # builds Go plugins found under src/Server/Plugins/*
make install-all-plugins  # stages plugins to ~/.PrometheanProxy/plugins
```

3) Build the Go implant binaries

```bash
make linux windows
```

## Configuration
- Server config: `~/.PrometheanProxy/config.toml`
   - Auto-created on first run (copied from `src/Server/config.toml`)
   - Controls listen address, webPort (beacon HTTP), logging, and module locations
- Obfuscation map: `src/Server/obfuscate.json`
   - Server loads it directly; the client reads the same mapping via the `-obfuscate` flag or ldflags (passed by Makefile)
   - You can change JSON field names for implant info and commands, plus module name obfuscation
- Plugin name obfuscation: each plugin can ship its own `obfuscate.json` (e.g., `src/Server/Plugins/netstat/obfuscate.json`) to change the advertised name at the wire level
- HMAC: a key can be injected at build time from `~/.PrometheanProxy/Certificates/hmac.key` (used by the Makefile). Plumbed through the client as `-hmac-key` and ldflags; integration is WIP.

## Usage
### Start the server (source or packaged)
- Run from source:
```bash
PYTHONPATH=src python3 src/Server/server.py
```
- Or run packaged ELF (after `make server`):
```bash
./bin/PrometheanProxy
```

The beacon HTTP server listens on the address/port from `config.toml` (plain HTTP by design).

### Run the implant
- Build and run quickly in debug with Make:
```bash
make run-client
```
- Or run a built binary with explicit flags:
```bash
./bin/promethean-client-linux-amd64-debug -conn=beacon -obfuscate=$(pwd)/src/Server/obfuscate.json
```

### Loading plugins (modules)
- From the server console, select a beacon and use the module loader to list and send a module. The server will:
   - Locate `~/.PrometheanProxy/plugins/<name>/<channel>/<name>[ -debug].{so|dll}`
   - Base64 the artifact and queue a `module` command to the beacon using the obfuscated module name
   - The implant caches the bytes in-memory and executes the plugin lazily on demand


## Remote management client (WIP)
`src/RemoteServer/` contains an experimental remote admin client that connects to the server over TLS and an additional app-layer ECDH step. It supports simple authentication and listing/selection of implants. Expect changes as this matures.

## Testing
Run the Python unit tests for server utilities and auth components:

```bash
make test
```

## Contributing
Contributions are welcome. Please open issues and submit pull requests.

## License
See [LICENSE](LICENSE) for details.

## Future work
- Tighten HMAC-backed request auth across beacon and session flows
- Expand remote management client features (commands, uploads, richer TUI)
- Additional built-in commands and example plugins
- Optional web UI for monitoring (investigation ongoing)

## Disclaimer
This project is for authorized testing and research only. Use requires explicit permission from all parties.
