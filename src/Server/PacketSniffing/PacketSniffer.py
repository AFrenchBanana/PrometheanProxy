"""
Packet sniffer function that takes in raw data and can either 
decode ethernet and IP headers or send raw bytes to a file  
"""

import socket
import struct 
import threading
import ssl
from Modules.global_objects import *
from Modules.content_handler import TomlFiles
from Modules.authentication import Authentication
from Modules.global_objects import send_data, receive_data, connectiondetails
import sys


class PacketSniffer:
    """Packet Sniffer function, can intercept packets on a raw socket"""
    def __init__(self):
        with TomlFiles("config.toml") as f: # loads the config files
            config = f
            #loads global variables
        global snifferdetails, snifferaddress
        snifferdetails = []
        snifferaddress = []

    def start_raw_socket(self):
        """starts a raw socket wrapped in SSL"""
        global SSL_Socket
        self.address = config['packetsniffer']['listenaddress'], config['packetsniffer']['port'] # gets the address from the config
        #sets the context for the SSl Socket
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=config['packetsniffer']['TLSCertificate'], keyfile=config['packetsniffer']['TLSkey'])
        socket_clear = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        SSL_Socket = context.wrap_socket(socket_clear, server_side=True)
        try:
            SSL_Socket.bind(self.address) # binds the socket
        except OSError:
            print(f"{self.address[0]}:{self.address[1]} already in use")
            sys.exit(1)
        SSL_Socket.listen()
        #starts a new thead to the client handler toallow multiple connections,
        listenerthread = threading.Thread(target=self.accept_raw_connection, args=()) # threads the accept
        listenerthread.start() #start the thread
        return


    def accept_raw_connection(self):
        """Function that listens for connections and handles them by inserting htem to sniffer lists to make them referencable.
        once accepted it ensures a connection is also established on the main port, and then starts the listener
        """
        #Loop that handles new connections
        i = 0
        while True:
            conn, r_address = SSL_Socket.accept() #accepts the connection
            for connections in connectionaddress:
                if connections[0] == r_address[0]: # checks if the IP is in the main socket
                    snifferdetails.append(conn) # adds to the list
                    snifferaddress.append(r_address) # adds to the list
                    sharkthread = threading.Thread(target=self.listener, args=(str(i))) # initalises the listener thread
                    sharkthread.start() #start the thread
                    i += 1
                else:
                    conn.close() 


    def listener(self, i):
        """listener that can either decode raw packets or write to a file"""
        i = int(i) # reference for list
        sudo = str(snifferdetails[i].recv(8).decode()) # checks if sudo is enabled
        if sudo == "0": # if sudo is enabled on client
            if config['packetsniffer']['debugPrint'] == True: # if packet sniffer logging is on config
                while True:
                    try:
                        packetbyte = 0
                        data = snifferdetails[i].recv(65535) # recives packets

                        #unpacks mac adresses and ether type
                        ethernet_header = data[:14] # grabs the ethernet header
                        ethernet_header_tuple = struct.unpack("!6s6sH", ethernet_header) # decodes the ethernet header
                        source_mac = ":".join("{:02x}".format(x) for x in ethernet_header_tuple[0]) # grabs the source mac
                        destination_mac = ":".join("{:02x}".format(x) for x in ethernet_header_tuple[1]) # grabs the dest mac
                        ethertype = ethernet_header_tuple[2] #ether type frame
                        packetbyte += 14 # tracks how many bytes have been used
                    

                        if ethertype == 0x0806: # arp header
                            arp_header_format = '!HHBBH6s4s6s4s'
                            arp_header = struct.unpack(arp_header_format, data[14:42])
                            hardware_type = arp_header[0]
                            protocol_type = arp_header[1]
                            hardware_type = arp_header[2]
                            protocol_size = arp_header[3]
                            opcode = arp_header[4]
                            sender_ip = '.'.join(map(str, arp_header[6]))
                            target_ip = '.'.join(map(str, arp_header[8]))
                            if opcode == 1:
                                print(f"Source Mac: {source_mac} SourceIP: {sender_ip} ARP Request: Who is {target_ip}")
                            if opcode == 2:
                                print(f"Source Mac: {source_mac} SourceIP: {sender_ip} ARP Reply: {source_mac} is {target_ip}")
                            

                        
                        elif ethertype in (0x0800, 2048): #IPv4
                            end_index = packetbyte + 20
                            ip4_header = data[packetbyte:end_index] # gets the ip header
                            ip4_header_tuple = struct.unpack("!BBHHHBBH4s4s", ip4_header) # decodes the IP header
                            ip4version = ip4_header_tuple[0] >> 4 # ip version
                            ip4_header_length = (ip4_header_tuple[0] & 0x0F) * 4 # header length
                            ip4_type_of_service = ip4_header_tuple[1]
                            payload_length = ip4_header_tuple[2] # total length
                            ip4_identiicaiton = ip4_header_tuple[3]
                            ip4_flags_fragment_offset = ip4_header_tuple[4]
                            ttl = ip4_header_tuple[5]
                            transport_protocol = ip4_header_tuple[6]
                            ip4_header_checksum = [7]
                            source_ip = socket.inet_ntoa(ip4_header_tuple[8]) # src ip
                            dest_ip = socket.inet_ntoa(ip4_header_tuple[9]) #dest ip
                            packetbyte += 20

                        elif ethertype in (0x86DD, 34525): # IPv6
                            end_index = packetbyte + 40
                            ip6_header = data[packetbyte:end_index]
                            ip6_header_format = '!IHBB16s16s'
                            ip6_header_tuple = struct.unpack(ip6_header_format, ip6_header)
                            ip6_version = (ip6_header_tuple[0] >> 28) & 0xF
                            ip6_traffic_class = (ip6_header_tuple[0] >> 20) & 0xFF
                            ip6_flow_label = ip6_header_tuple[0] & 0xFFFF
                            payload_length = ip6_header_tuple[1]
                            transport_protocol = ip6_header_tuple[2]
                            ttl = ip6_header_tuple[3]
                            source_ip = ip6_header_tuple[4]
                            dest_ip = ip6_header_tuple[5]
                            packetbyte += 40

        
                        if transport_protocol == 6: #tcp
                            end_index = packetbyte + 20
                            transport_protocol = "TCP"
                            tcp_header_format = '!HHLLBBHHH'
                            tcp_packet = data[packetbyte:end_index]
                            tcp_tuple = struct.unpack(tcp_header_format, tcp_packet)
                            source_port = tcp_tuple[0]
                            dest_port = tcp_tuple[1]
                            tcp_sequence_number = tcp_tuple[2]
                            tcp_ack_num = tcp_tuple[3]
                            tcp_data_offset = tcp_tuple[4] & 0x0FFF
                            tcp_window = tcp_tuple[5]
                            tcp_checksum = tcp_tuple[6]
                            tcp_urgent_point = tcp_tuple[7]
                            packetbyte += 20
                            print(f"Source Mac: {source_mac} Destination Mac {destination_mac} SourceIP = {source_ip} destIP = {dest_ip} TTL: {ttl} {transport_protocol} SrcPort: {source_port} DestPort: {dest_port}") # prints packet


                        elif transport_protocol == 17: #udp
                            end_index = packetbyte + 8
                            udp_packet_data= data[packetbyte:end_index]
                            transport_protocol == "UDP"
                            udp_header_format = '!HHHH'
                            udp_header_tuple = struct.unpack(udp_header_format, udp_packet_data)
                            source_port = udp_header_tuple[0]
                            dest_port = udp_header_tuple[1]
                            udp_length = udp_header_tuple[2]
                            udp_checksum = udp_header_tuple[3]
                            print(f"Source Mac: {source_mac} Destination Mac {destination_mac} SourceIP = {source_ip} destIP = {dest_ip} TTL: {ttl} {transport_protocol} SrcPort: {source_port} DestPort: {dest_port}") # prints packet
                    except:
                        pass


            else: # if debug logg turned off write to file
                with open(f"./PacketSniffing/{(snifferaddress[i])}.bytes", "wb") as file:
                    while True:
                        data = snifferdetails[i].recv(65535)
                        file.write(data)
                        
        else:
            pass