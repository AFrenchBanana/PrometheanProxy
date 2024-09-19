# C2 Server

**This tool is only to be used with consent with all parties involed**

## Contents
1. [Features](#features)
2. [Client Features](#client-features)
3. [Usage](#usage)
4. [MultiHandler Menu](#multihandler-menu)
5. [Session Commands](#session-commands)
6. [Technical Details](#technical-details)
7. [Database](#database)
8. [Server COnfiguration](#server-configuration)
9. [Other Technical Details](#other-technical-details)
10. [Packet Sniffer](#packet-sniffer)

## Features

Fully working client + socket server with the abiliy to handle multiple clients and TLS encryption on each socket. 

The server has full database support storing returned data from the client as well as a list of known safe hashes to compare against. 

Partial Working client written in C


### Client Features
Each client is able to provide a number of useful features:

1. File upload and file download support
2. An interactive shell
3. The ability to list running processes and CPU usage (Linux only)
4. The ability to list service and their state (Linux only)
5. Hash files and compare the hash against known good binaries
6. Packet sniffing with partial packet decoding / write to file **(experimental)** (sudo only)
7. List connections on the target from netstat (Linux only)
8. Disk usuage statistics
9. System info command
10. Directory Listing
11. Authentication to prevent rogue clients connection

All of these features *(except shell)* work without using binaries on the system and purley off reading and formating files. 

## Usage

Before starting the server please ensure you are happy with the config file configuration. A rundown of each entry can be found in the relevant subsection. 

Please ensure the folder structure is correct

To start the the server run the file `server.py` with either `./server.py` or `python3 server.py` 

### Multihandler menu

Within the multihandler menu typing anyting other than a correct command will show you the help menu.

#### Commands
1. list - This will show all available session commands
2. Sessions - type this to connect to a session
3. close - close 1 session
4. closeall - closes all sessions
5. hashfiles - hash local files and store them in the database 
6. exit - closes the server

### Session Commands
Once in a session you are able to directly talk to the client. Like the multihandler menu, any thing other than a recongised command will show the help menu. 

#### Commands
1. shell - Spawn a semi-interactive shell, type exit to return
2. close - closes the current sessions
3. Download - Download a file from the client to yout host.
4. Upload - Upload a file from the server to the client
5. sysinfo - List system info on the client
6. Processes - list processes and CPU usuage on the client
7. Servces - List servics and their state
8. checkfiles - Compare binaries against binaries in the database
9. listdir - list a directory
10. exit - return to the multihandler without closing the session
11. netstat - list netstat connetions

None of these commands apart from `shell` directly call any binaries. Instead read files and do processing to make them readable


## Technical Details

### Client
The client will attempt to connect and if it doesn't connect, it waits 5seconds before trying again. 

If the connection drops it restablishes the socket and re-attempts to connect and then wait 5seconds.

### Behind the scenes
Once the server is loaded onto the target the class in the multi handler menu is loaded and sockets are initialised. 

Once everything has been setup the user is spawned into the multihandler fuction.

From here when they wish to execute a multi_handler command, the command is a function referenced within the multi_handler_commands file. 

Once connected to a session the commands are executed from within the sessions_commands file. 

The global objects contains functions and variables that need to be accessed anywhere to prevent circular importing issues. 

There is also a dedicated file to handle the database, authentication and packet sniffer.


#### Database
The database runs on sqlite3.

Upon initial launch the server checks the file exists and if not will create a file, once this is done it checks all the tables exist and will create them if not.

Within the config file the data base location can be changed using the `file` tag. 

If the `addData` is set to false no entries will be stored within the database

Finally tables and their schemas are stored here, currently the tables are:
1. Addresses
2. Shell
3. Processes
4. Services
5. Netstat
6. SystemInfo
7. Hashes
8. Disk

#### Server Configuration
The server has a number of configuration options within the confg file

`listenadress` By default this should be set to "0.0.0.0" unless you want to only listen on a specific adress.

`listenport` The port number you wish to listen on

##### TLS
The server has the ability to detect and create TLS certificates. 

The path to where they are stored should be placed in the options: `TLSCertificate` and `TLSkey`. If this path is not correct and the server doesn't detect these, it will generate them.


Once a client connects it will share the keys and encrypt the traffic

##### Authentication

To prevent rogue clients from connecting a basic authentication method is implemented.

1. The server generates a random ascii string (The length is specified with `keylength`) upon client connection.
2. This string is sent over the socket. 
3. Both sides add the clients port to the end of the string, reverse the entire string and then hash it with a sha512 hash.
4. The client sends the hash to the server.
5. The server checks the clients message and if it doesnt match its own, it drops the client.

##### Other Technical Details

Both the client and server are configured to send data in chunks of 4096bytes, until all the data is sent and on the final *(or first if not bigger than 4096)* packet only send the required amount of bytes. 

This is achieved using struct to send a header packer contaning the buffer size and total length


##### Packet Sniffer

**This feature is still experimental**

It is likely to throw more errors and should not be currently used if stability is important.

##### Features
sudo check

packet header decode

write to files

authentication

encryption

##### Config options
`active` - if set to true, the client 

`listenaddress` - this should be the same as the server unless you only want to listen to 1 clent

`Port` - this needs to be a different port to the server port

TLS keys should be the same as the server (these currently do not autogenerate)

`debugPrint` - if true the partial decode will show on screen (this will make the multihandler unusable), if this is set to false the raw data will write to a file.

##### How it works

1. Upon succesful authentication from a client. The server will send `active` to tell the client whether this feature is enabled
2. If not active the program continues as normal. If active the client will then call the listner function
3. The server sends the second port number across
4. The client will run a sudo check as this feature requires sudo right
5. Without sudo rights the function is returned otherwise a raw socket is established.
6. The client threads this socket and connects to the servers second socket.
7. Once connected the server checks if this IP is connected to its other socket, if not it will drop the connection. This prevents rogue clients connecting
7. All data the client recieves is sent to the server.
8. The server will either write to the file or print to the screen (config depedant)
<<<<<<< HEAD

## C Client 

This is still in early syages of development and is not reccomended to be use.

Current working features include:
1.Full intergration with original python server.

2. Can be used at the same time as the python client.

3. Sysinfo working 

4. Authentication and SSL implemented.  

