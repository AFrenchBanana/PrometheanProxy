# PrometheanProxy Architecture

This document provides a high-level overview of the PrometheanProxy architecture, detailing the server, the client (implant), and their interaction.

## High-Level Flow

The basic operational flow consists of the C2 Server listening for connections from implants running on compromised machines. All interaction and data exfiltration is managed through this central server.

```
+----------------+      +---------------+      +-----------------+
| Operator(s)    |----->| C2 Server     |<---->| Implant (Client)|
| (via Console)  |      | (Python)      |      | (Go)            |
+----------------+      +---------------+      +-----------------+
                          |
                          | listens for connections
                          |
      +------------------------------------------------+
      |                   Internet                     |
      +------------------------------------------------+
```

## Server Architecture (Python)

The server is the core of the framework, built with Python. It's responsible for managing implants, handling operator commands, and serving plugins.

```
+-----------------------------------------------------------+
| PrometheanProxy Server                                    |
| +--------------------+   +---------------------------+    |
| | Multi-Handler Core |   | RESTful API (for console) |    |
| +--------------------+   +---------------------------+    |
|           |                           |                   |
| +--------------------+   +---------------------------+    |
| | Beacon HTTP Server |<->| Session Manager           |    |
| +--------------------+   +---------------------------+    |
|           |                           |                   |
| +--------------------+   +---------------------------+    |
| | Plugin Manager     |<->| Command Queue             |    |
| +--------------------+   +---------------------------+    |
|                                |                          |
|                       +------------------+                |
|                       | SQLite Database  |                |
|                       +------------------+                |
+-----------------------------------------------------------+
```

- **Multi-Handler Core:** The central component that manages different listeners and handlers (e.g., for beacons, sessions).
- **Beacon HTTP Server:** Listens for incoming connections from new implants.
- **Session Manager:** Manages active interactive sessions with implants.
- **Plugin Manager:** Handles the loading, delivery, and management of Go plugins for the clients.
- **Command Queue:** A queue for commands sent from the operator to the implant.
- **SQLite Database:** Stores persistent information about the C2 state.
- **RESTful API:** Provides an interface for front-end clients, like the command-line console, to interact with the server.


## Client Architecture (Go)

The client, or implant, is a lightweight and high-performance agent written in Go. It runs on the target machine, beacons back to the server, and executes commands.

```
+------------------------------------------------------+
| PrometheanProxy Implant (Go)                         |
|                                                      |
| +------------------+        +----------------------+ |
| | Beaconing Module |<------>| Configuration        | |
| | (HTTP)           |        | (Server URL, Keys)   | |
| +------------------+        +----------------------+ |
|         |                                            |
| +------------------+        +----------------------+ |
| | Session Handler  |<------>| Command Executor     | |
| +------------------+        +----------------------+ |
|         |                   /           \            |
| +------------------+   +------------------+          |
| | File System I/O  |   | Shell Commands   |          |
| +------------------+   +------------------+          |
|                          |                           |
|                  +--------------------------+        |
|                  | RPC Client for Plugins   |        |
|                  +--------------------------+        |
|                                                      |
+------------------------------------------------------+
```

- **Beaconing Module:** Periodically contacts the C2 server to check for new commands.
- **Configuration:** Holds the configuration for the implant, such as the C2 server URL and encryption keys.
- **Session Handler:** Manages the interactive session with the C2 server.
- **Command Executor:** Executes commands received from the server. This can be a built-in command or a dynamically loaded plugin.
- **RPC Client for Plugins:** The client can load and execute Go plugins at runtime via an RPC mechanism. This allows for dynamic extension of the implant's capabilities.
