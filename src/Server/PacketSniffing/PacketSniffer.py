"""
Packet sniffer function that takes in raw data and can either
decode ethernet and IP headers or send raw bytes to a file
"""

import socket
import struct
import threading
import ssl
from Modules.global_objects import config, sessions_list
import sys


class PacketSniffer:
    """Packet Sniffer function, can intercept packets on a raw socket"""

    def __init__(self):
        global snifferdetails, snifferaddress
        snifferdetails = []
        snifferaddress = []

    def start_raw_socket(self):
        """starts a raw socket wrapped in SSL"""
        global SSL_Socket
        # gets the address from the config
        self.address = (config['packetsniffer']['listenaddress'],
                        config['packetsniffer']['port'])
        # sets the context for the SSl Socket
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=config['packetsniffer']['TLSCertificate'],
            keyfile=config['packetsniffer']['TLSkey'])
        socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        SSL_Socket = context.wrap_socket(socket_clear, server_side=True)
        try:
            SSL_Socket.bind(self.address)  # binds the socket
        except OSError:
            print(f"{self.address[0]}:{self.address[1]} already in use")
            sys.exit(1)
        SSL_Socket.listen()
        # starts a new thead to the client handler toallow multiple
        # connections,
        listenerthread = threading.Thread(
            target=self.accept_raw_connection,
            args=())  # threads the accept
        listenerthread.start()  # start the thread
        return

    def accept_raw_connection(self):
        """
        Function that listens for connections and handles
        them by inserting htem to sniffer lists to make them referencable.
        once accepted it ensures a connection is also established on the
        main port, and then starts the listener
        """
        # Loop that handles new connections
        i = 0
        while True:
            conn, r_address = SSL_Socket.accept()  # accepts the connection
            for sessionID, connection in sessions_list.items():
                # checks if the IP is in the main socket
                if connection.details == r_address[0]:
                    snifferdetails.append(conn)  # adds to the list
                    snifferaddress.append(r_address)  # adds to the list
                    sharkthread = threading.Thread(
                        target=self.listener, args=(
                            str(i)))  # initalises the listener thread
                    sharkthread.start()  # start the thread
                    i += 1
                else:
                    conn.close()

    def listener(self, i):
        """
        listener that can either decode raw packets or write to a file
        """
        i = int(i)  # reference for list
        # checks if sudo is enabled
        sudo = str(snifferdetails[i].recv(8).decode())
        if sudo == "0":  # if sudo is enabled on client
            # if packet sniffer logging is on config
            if config['packetsniffer']['debugPrint']:
                while True:
                    try:
                        packetbyte = 0
                        data = snifferdetails[i].recv(65535)  # recives packets

                        # unpacks mac adresses and ether type
                        # grabs the ethernet header
                        ethernet_header = data[:14]
                        ethernet_header_tuple = struct.unpack(
                            "!6s6sH", ethernet_header)

                        source_mac = ":".join(
                            "{:02x}".format(x) for x in
                            ethernet_header_tuple[0])  # grabs the source mac

                        destination_mac = ":".join(
                            "{:02x}".format(x) for x in
                            ethernet_header_tuple[1])  # grabs the dest mac

                        # ether type frame
                        ethertype = ethernet_header_tuple[2]
                        packetbyte += 14

                        if ethertype == 0x0806:  # arp header
                            arp_header_format = '!HHBBH6s4s6s4s'
                            arp_header = struct.unpack(
                                arp_header_format, data[14:42])
                            _ = arp_header[0]  # grabs the hardware type
                            _ = arp_header[1]  # grabs the protocol type
                            _ = arp_header[2]  # grabs the hardware size
                            _ = arp_header[3]  # grabs the protocol size
                            opcode = arp_header[4]
                            sender_ip = '.'.join(map(str, arp_header[6]))
                            target_ip = '.'.join(map(str, arp_header[8]))
                            if opcode == 1:
                                print(f"Source Mac: {source_mac} SourceIP: " +
                                      f"{sender_ip} ARP Request: Who is " +
                                      target_ip)
                            if opcode == 2:
                                print(f"Source Mac: {source_mac} SourceIP: " +
                                      f"{sender_ip} ARP Reply: " +
                                      f"{source_mac} is {target_ip}")

                        elif ethertype in (0x0800, 2048):  # IPv4
                            end_index = packetbyte + 20
                            # gets the ip header
                            ip4_header = data[packetbyte:end_index]
                            # unpacks the ip header
                            ip4_header_tuple = struct.unpack(
                                "!BBHHHBBH4s4s", ip4_header)
                            _ = ip4_header_tuple[0] >> 4  # ip version
                            _ = (
                                ip4_header_tuple[0] & 0x0F) * 4
                            _ = ip4_header_tuple[1]  # type of service

                            _ = ip4_header_tuple[2]  # total length
                            _ = ip4_header_tuple[3]  # identification
                            _ = ip4_header_tuple[4]  # flags
                            ttl = ip4_header_tuple[5]
                            transport_protocol = ip4_header_tuple[6]
                            _ = [7]  # checksum
                            source_ip = socket.inet_ntoa(
                                ip4_header_tuple[8])  # src ip
                            dest_ip = socket.inet_ntoa(
                                ip4_header_tuple[9])  # dest ip
                            packetbyte += 20

                        elif ethertype in (0x86DD, 34525):  # IPv6
                            end_index = packetbyte + 40
                            ip6_header = data[packetbyte:end_index]
                            ip6_header_format = '!IHBB16s16s'
                            ip6_header_tuple = struct.unpack(
                                ip6_header_format, ip6_header)
                            _ = (ip6_header_tuple[0] >> 28) & 0xF
                            _ = (
                                ip6_header_tuple[0] >> 20) & 0xFF
                            _ = ip6_header_tuple[0] & 0xFFFF
                            _ = ip6_header_tuple[1]
                            transport_protocol = ip6_header_tuple[2]
                            ttl = ip6_header_tuple[3]
                            source_ip = ip6_header_tuple[4]
                            dest_ip = ip6_header_tuple[5]
                            packetbyte += 40

                        if transport_protocol == 6:  # tcp
                            end_index = packetbyte + 20
                            transport_protocol = "TCP"
                            tcp_header_format = '!HHLLBBHHH'
                            tcp_packet = data[packetbyte:end_index]
                            tcp_tuple = struct.unpack(
                                tcp_header_format, tcp_packet)
                            source_port = tcp_tuple[0]
                            dest_port = tcp_tuple[1]
                            _ = tcp_tuple[2]  # sequence number
                            _ = tcp_tuple[3]  # ack number
                            _ = tcp_tuple[4] & 0x0FFF  # data offset
                            _ = tcp_tuple[5]  # flags
                            _ = tcp_tuple[6]  # window
                            _ = tcp_tuple[7]  # checksum
                            packetbyte += 20
                            print(f"Source Mac: {source_mac} Destination Mac ",
                                  destination_mac,
                                  f"SourceIP = {source_ip} destIP = {dest_ip} "
                                  f"TTL: {ttl} {transport_protocol} "
                                  f"SrcPort: {source_port} DestPort: ",
                                  dest_port)

                        elif transport_protocol == 17:  # udp
                            end_index = packetbyte + 8
                            udp_packet_data = data[packetbyte:end_index]
                            transport_protocol == "UDP"
                            udp_header_format = '!HHHH'
                            udp_header_tuple = struct.unpack(
                                udp_header_format, udp_packet_data)
                            source_port = udp_header_tuple[0]
                            dest_port = udp_header_tuple[1]
                            _ = udp_header_tuple[2]  # length
                            _ = udp_header_tuple[3]  # checksum
                            print(f"Source Mac: {source_mac} Destination Mac ",
                                  destination_mac,
                                  f"SourceIP = {source_ip} destIP = {dest_ip} "
                                  f"TTL: {ttl} {transport_protocol} "
                                  f"SrcPort: {source_port} DestPort: ",
                                  dest_port)
                    except BaseException:
                        pass

            else:  # if debug logg turned off write to file
                with (open(
                        f"./PacketSniffing/{(snifferaddress[i])}.bytes", "wb")
                        as file):
                    while True:
                        data = snifferdetails[i].recv(65535)
                        file.write(data)

        else:
            pass
