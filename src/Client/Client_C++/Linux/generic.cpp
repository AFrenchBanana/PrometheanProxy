#include <iostream>
#include <vector>
#include <string>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>


// Get the IP addresses of the local machine and return them as a vector of strings
std::vector<std::string> getIPAddresses() {
    std::vector<std::string> ipAddresses;
    struct ifaddrs *interfaces = nullptr;
    struct ifaddrs *tempAddr = nullptr;

    if (getifaddrs(&interfaces) == 0) {
        tempAddr = interfaces;
        while (tempAddr != nullptr) {
            if (tempAddr->ifa_addr->sa_family == AF_INET) {
                char addressBuffer[INET_ADDRSTRLEN];
                void *addrPtr = &((struct sockaddr_in *)tempAddr->ifa_addr)->sin_addr;
                inet_ntop(AF_INET, addrPtr, addressBuffer, INET_ADDRSTRLEN);
                ipAddresses.push_back(addressBuffer);
            }
            tempAddr = tempAddr->ifa_next;
        }
    }
    freeifaddrs(interfaces);
    return ipAddresses;
}

std::string getHostname() {
    char hostname[1024];
    hostname[1023] = '\0';
    if (gethostname(hostname, 1023) == -1) {
        throw std::runtime_error("Failed to get hostname");
    }
    return std::string(hostname);
}
