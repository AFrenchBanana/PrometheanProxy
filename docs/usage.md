# Usage Guide

This guide provides a step-by-step walkthrough on how to set up and use PrometheanProxy.

## 1. Installation and Setup

First, you need to install the necessary prerequisites and set up the server environment.

**Prerequisites:**
- Go 1.20+
- Python 3.12+
- `make` and a C/C++ toolchain (like `gcc`)

**Setup:**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AFrenchBanana/PrometheanProxy.git
    cd PrometheanProxy
    ```

2.  **Create a Python virtual environment:**
    ```bash
    make venv
    ```
    This will install all the necessary Python dependencies.

3.  **Build the server and plugins:**
    ```bash
    make server
    make plugins
    ```
    This creates a standalone executable for the server in the `bin/` directory and compiles all the Go plugins located in `src/Server/Plugins/`.

4. **Install Plugins:**
   ```bash
   make install-all-plugins
   ```
   This command stages the plugins to the appropriate directory (`~/.PrometheanProxy/plugins`) so the server can find them.


## 2. Running the Server

Once the setup is complete, you can start the C2 server.

```bash
./bin/PrometheanProxy
```

The server will start and listen for incoming connections on the port specified in the configuration file (`config.toml`).

## 3. Generating an Implant

Next, you need to build the client implant. The `Makefile` provides helpers for this.

- **For Linux:**
  ```bash
  make linux
  ```
- **For Windows:**
  ```bash
  make windows
  ```

This will generate both release and debug versions of the implant in the `bin/` directory (e.g., `bin/promethean-client-linux-amd64`).

## 4. Deploying and Running the Implant

Copy the generated implant to your target machine. Once on the target, execute it.

For example, on a Linux target:
```bash
./promethean-client-linux-amd64
```

The implant will start beaconing back to the C2 server.

## 5. Interacting with Beacons and Sessions

Once an implant checks in, it will appear as a new beacon in your server console.

1.  From the main menu in the PrometheanProxy console, select the `beacons` handler.
2.  You will see a list of active beacons. You can select a beacon by its ID to interact with it.
3.  Once interacting with a beacon, you can issue commands, or upgrade the beacon to an interactive `session`.

## 6. Using Plugins (Modules)

PrometheanProxy's power comes from its dynamic plugin system.

1.  While interacting with a beacon or session, use the `module` command to see available plugins.
2.  You can then load a module, which will send the compiled Go plugin to the implant.
    ```
    module load <plugin_name>
    ```
3.  Once loaded, the new command provided by the plugin will be available to use in the implant's shell. For example, after loading the `netstat` plugin, you can run the `netstat` command on the remote host.
