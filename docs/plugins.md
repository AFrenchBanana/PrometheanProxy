# PrometheanProxy Plugins

The plugin system is a core feature of PrometheanProxy, allowing for dynamic extension of the implant's capabilities at runtime. This document explains how plugins work and lists the currently available plugins.

## How Plugins Work

PrometheanProxy plugins are self-contained modules, typically written in Go, that can be sent over the network to a live implant.

1.  **Development:** A plugin is written in Go and implements a specific RPC interface that the main implant understands. The `src/Server/Plugins/template` directory provides a clean boilerplate for creating new plugins.
2.  **Compilation:** The `Makefile` automatically discovers and compiles any subdirectory in `src/Server/Plugins/` that contains a `main.go` file into a shared object (`.so` for Linux) or dynamic-link library (`.dll` for Windows).
3.  **Staging:** The server, upon startup, knows the location of these compiled plugins.
4.  **Loading:** From the C2 console, an operator can issue a `module load <plugin_name>` command for a specific beacon.
5.  **Delivery:** The server reads the appropriate compiled plugin artifact from disk, base64-encodes it, and sends it to the implant as a command.
6.  **Execution:** The implant receives the plugin, loads it into memory, and can then execute the new functionality it provides. The implant uses the HashiCorp `go-plugin` library to manage this as an RPC-style system.

This architecture means you don't need to recompile or redeploy the entire implant to add new features.

## Available Plugins

The following plugins are included with PrometheanProxy:

| Plugin              | Description                                                               |
| ------------------- | ------------------------------------------------------------------------- |

| `netstat`           | Lists active network connections, similar to the `netstat` command.       |
| `processes`         | Lists running processes on the remote system.                             |
| `shell`             | Provides a full interactive shell (`/bin/bash` or `cmd.exe`) on the target. |
| `system_info`       | Gathers and returns basic system information (OS, architecture, etc.).    |
| `whoami`            | Returns the user context that the implant is running as.                  |

## Creating Your Own Plugin

To create a new plugin:

1.  Copy the `src/Server/Plugins/template` directory to a new directory, for example, `src/Server/Plugins/my_new_plugin`.
2.  Modify the `main.go` file within your new plugin's directory to implement your desired functionality.
3.  The build system will automatically detect your new plugin the next time you run `make plugins`.
4.  After running `make install-all-plugins`, your new plugin will be available to load from the server console.
