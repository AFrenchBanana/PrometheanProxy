# PrometheanProxy C2
```text   ___                          _   _                        ___                     
  / _ \_ __ ___  _ __ ___   ___| |_| |__   ___  __ _ _ __   / _ \_ __ _____  ___   _ 
 / /_)/ '__/ _ \| '_ ` _ \ / _ \ __| '_ \ / _ \/ _` | '_ \ / /_)/ '__/ _ \ \/ / | | |
/ ___/| | | (_) | | | | | |  __/ |_| | | |  __/ (_| | | | / ___/| | | (_) >  <| |_| |
\/    |_|  \___/|_| |_| |_|\___|\__|_| |_|\___|\__,_|_| |_\/    |_|  \___/_/\_\\__, |
                                                                               |___/ 
```

**This tool is only to be used with consent from all parties involved**

## Contents
1. [Features](#features)
2. [Client Features](#client-features)
3. [Usage](#usage)
4. [MultiHandler Menu](#multihandler-menu)
5. [Session Commands](#session-commands)
6. [Technical Details](#technical-details)
7. [Database](#database)
8. [Server Configuration](#server-configuration)
9. [Other Technical Details](#other-technical-details)
10. [Packet Sniffer](#packet-sniffer)

## Features

Fully working client + socket server with the ability to handle multiple clients and TLS encryption on each socket.

The server has full database support, storing returned data from the client as well as a list of known safe hashes to compare against.

Partially working client written in C.

### Client Features
Each client is able to provide a number of useful features:

1. File upload and file download support.
2. An interactive shell.
3. The ability to list running processes and CPU usage (Linux only).
4. The ability to list services and their state (Linux only).
5. Hash files and compare the hash against known good binaries.
6. Packet sniffing with partial packet decoding/write to file **(experimental)** (sudo only).
7. List connections on the target from netstat (Linux only).
8. Disk usage statistics.
9. System info command.
10. Directory listing.
11. Authentication to prevent rogue clients from connecting.

All of these features *(except shell)* work without using binaries on the system and purely off reading and formatting files.

## Usage

Before starting the server, please ensure you are happy with the config file configuration. A rundown of each entry can be found in the relevant subsection.

Please ensure the folder structure is correct.

To start the server, run the file `server.py` with either `./server.py` or `python3 server.py`.

### MultiHandler Menu

Within the multi-handler menu, typing anything other than a correct command will show you the help menu.

#### Commands
1. list - This will show all available session commands.
2. Sessions - Type this to connect to a session.
3. close - Close 1 session.
4. closeall - Close all sessions.
5. hashfiles - Hash local files and store them in the database.
6. exit - Close the server.

### Session Commands
Once in a session, you are able to directly talk to the client. Like the multi-handler menu, anything other than a recognized command will show the help menu.

#### Commands
1. shell - Spawn a semi-interactive shell, type exit to return.
2. close - Close the current session.
3. download - Download a file from the client to your host.
4. upload - Upload a file from the server to the client.
5. sysinfo - List system info on the client.
6. processes - List processes and CPU usage on the client.
7. services - List services and their state.
8. checkfiles - Compare binaries against binaries in the database.
9. listdir - List a directory.
10. exit - Return to the multi-handler without closing the session.
11. netstat - List netstat connections.

None of these commands, apart from `shell`, directly call any binaries. Instead, they read files and do processing to make them readable.

## Technical Details

### Client
The client will attempt to connect and if it doesn't connect, it waits 5 seconds before trying again.

If the connection drops, it re-establishes the socket and re-attempts to connect, then waits 5 seconds.

### Behind the Scenes
Once the server is loaded onto the target, the class in the multi-handler menu is loaded and sockets are initialized.

Once everything has been set up, the user is spawned into the multi-handler function.

From here, when they wish to execute a multi_handler command, the command is a function referenced within the multi_handler_commands file.

Once connected to a session, the commands are executed from within the session_commands file.

The global objects contain functions and variables that need to be accessed anywhere to prevent circular importing issues.

There is also a dedicated file to handle the database, authentication, and packet sniffer.

### Database
The database runs on sqlite3.

Upon initial launch, the server checks if the file exists, and if not, it will create the file. Once this is done, it checks if all the tables exist and will create them if not.

Within the config file, the database location can be changed using the `file` tag.

If `addData` is set to false, no entries will be stored within the database.

Finally, tables and their schemas are stored here. Currently, the tables are:
1. Addresses
2. Shell
3. Processes
4. Services
5. Netstat
6. SystemInfo
7. Hashes
8. Disk

### Server Configuration
The server has a number of configuration options within the config file:

`listenaddress` - By default, this should be set to "0.0.0.0" unless you want to only listen on a specific address.

`listenport` - The port number you wish to listen on.

#### TLS
The server has the ability to detect and create TLS certificates.

The path to where they are stored should be placed in the options: `TLSCertificate` and `TLSKey`. If this path is not correct and the server doesn't detect these, it will generate them.

Once a client connects, it will share the keys and encrypt the traffic.

#### Authentication
To prevent rogue clients from connecting, a basic authentication method is implemented.

1. The server generates a random ASCII string (the length is specified with `keylength`) upon client connection.
2. This string is sent over the socket.
3. Both sides add the client's port to the end of the string, reverse the entire string, and then hash it with a SHA-512 hash.
4. The client sends the hash to the server.
5. The server checks the client's message and if it doesn't match its own, it drops the client.

### Other Technical Details
Both the client and server are configured to send data in chunks of 4096 bytes, until all the data is sent and on the final *(or first if not bigger than 4096)* packet only sends the required amount of bytes.

This is achieved using struct to send a header packet containing the buffer size and total length.

### Packet Sniffer

**This feature is still experimental**

It is likely to throw more errors and should not be currently used if stability is important.

#### Features
1. Sudo check.
2. Packet header decode.
3. Write to files.
4. Authentication.
5. Encryption.

#### Config Options
`active` - If set to true, the client will activate the packet sniffer.

`listenaddress` - This should be the same as the server unless you only want to listen to 1 client.

`port` - This needs to be a different port from the server port.

TLS keys should be the same as the server (these currently do not autogenerate).

`debugPrint` - If true, the partial decode will show on screen (this will make the multi-handler unusable). If this is set to false, the raw data will write to a file.

#### How It Works
1. Upon successful authentication from a client, the server will send `active` to tell the client whether this feature is enabled.
2. If not active, the program continues as normal. If active, the client will then call the listener function.
3. The server sends the second port number across.
4. The client will run a sudo check as this feature requires sudo rights.
5. Without sudo rights, the function is returned, otherwise a raw socket is established.
6. The client threads this socket and connects to the server's second socket.
7. Once connected, the server checks if this IP is connected to its other socket, if not, it will drop the connection. This prevents rogue clients from connecting.
8. All data the client receives is sent to the server.
9. The server will either write to the file or print to the screen (config dependent).

## C Client

This is still in early stages of development and is not recommended for use.

Current working features include:
1. Full integration with the original Python server.
2. Can be used at the same time as the Python client.
3. Sysinfo working.
4. Authentication and SSL implemented.
