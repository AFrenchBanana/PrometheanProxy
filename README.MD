# PrometheanProxy C2
```text   ___                          _   _                        ___                     
  / _ \_ __ ___  _ __ ___   ___| |_| |__   ___  __ _ _ __   / _ \_ __ _____  ___   _ 
 / /_)/ '__/ _ \| '_ ` _ \ / _ \ __| '_ \ / _ \/ _` | '_ \ / /_)/ '__/ _ \ \/ / | | |
/ ___/| | | (_) | | | | | |  __/ |_| | | |  __/ (_| | | | / ___/| | | (_) >  <| |_| |
\/    |_|  \___/|_| |_| |_|\___|\__|_| |_|\___|\__,_|_| |_\/    |_|  \___/_/\_\\__, |
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
PrometheanProxy C2 is a modular, extensible command-and-control framework designed for red team operations, written with a Go-based client and a Python-based server. It enables secure and flexible beaconing, command execution, file transfer, and more. Many features are a work in progress. 

## Features
- Multi-platform Go client with beacon and HTTP modules
- Python-based server supporting:
  - Beacon handling
  - Multi-handler command routing
  - Web UI for session management
  - Packet sniffing and lateral movement
  - SQLite-backed server database
- Modular architecture for easy extension
- Secure communications and URL obfuscation

## Architecture
### Client (Go)
- Implements beaconing, HTTP requests, and URL obfuscation
- Generic command plugins: shell, directory traversal, system info
- Session management and custom protocol support

### Server (Python)
- HTTP and socket servers for beacon callbacks and interactive sessions
- Multi-handler architecture for different command contexts
- Embedded Web UI for session monitoring
- PacketSniffer module for network capture

## Prerequisites
- Go 1.18+ (for client)
- Python 3.9+ (for server)
- pip for Python package management

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourorg/PrometheanProxy.git
   cd PrometheanProxy
   ```
2. Install Python dependencies:
   ```bash
   make venv
   ```
3. Build the Go client:
   ```bash
  make run client 
   ```

  Change the argument to beacon or session depending on what you need. (You will likey need to run the server first to make the HMAC key) 

## Configuration
1. Edit the server configuration in `~/PrometheanProxy/config.toml` to set network interfaces, ports, and paths.
2. (Optional) Adjust client settings in Go source under `src/Client/generic/config`.

## Usage
### Start the Server
```bash
python src/Server/server.py 
```

### Run the Client
```bash
./promethean-client
```

### Web UI
Open `http://<server_ip>:<web_ui_port>` in your browser to view active sessions.


## Contributing
Contributions are welcome! Please open issues and submit pull requests in the [GitHub repository](https://github.com/yourorg/PrometheanProxy).

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Future Features

- HMAC support on Beacon mode
- Binary compliation from server
- Remote module loading / staging 
- Continued work on web GUI 

## Disclaimer
**This tool is only to be used with consent from all parties involved.**
