#include <iostream>
#include <vector>
#include <string>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <stdexcept>

#include "../Generic/logging.hpp" 

// Get the IP addresses of the local machine and return them as a vector of strings
std::vector<std::string> getIPAddresses() {
    logger.log("Starting getIPAddresses");
    std::vector<std::string> ipAddresses;
    struct ifaddrs *interfaces = nullptr;
    struct ifaddrs *tempAddr = nullptr;

    if (getifaddrs(&interfaces) != 0) {
        logger.error("Failed to get network interfaces");
        return ipAddresses;
    }

    logger.log("Successfully retrieved network interfaces");
    tempAddr = interfaces;
    while (tempAddr != nullptr) {
        if (tempAddr->ifa_addr && tempAddr->ifa_addr->sa_family == AF_INET) {
            char addressBuffer[INET_ADDRSTRLEN];
            void *addrPtr = &((struct sockaddr_in *)tempAddr->ifa_addr)->sin_addr;
            inet_ntop(AF_INET, addrPtr, addressBuffer, INET_ADDRSTRLEN);
            ipAddresses.push_back(addressBuffer);
        }
        tempAddr = tempAddr->ifa_next;
    }
    freeifaddrs(interfaces);
    for (const auto& ip : ipAddresses) {
        logger.log("Found IP Address: " + ip);
    }
    logger.log("Completed getIPAddresses");
    return ipAddresses;
}

std::string getHostname() {
    logger.log("Starting getHostname");
    char hostname[1024];
    hostname[1023] = '\0';
    if (gethostname(hostname, 1023) == -1) {
        logger.error("Failed to get hostname");
    std::string hostnameStr(hostname);
    logger.log("Hostname: " + hostnameStr);
    return hostnameStr;
    }
    logger.log("Successfully retrieved hostname: " + std::string(hostname));
    return std::string(hostname);
}


