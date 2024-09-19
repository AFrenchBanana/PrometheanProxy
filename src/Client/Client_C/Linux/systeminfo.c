#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <sys/types.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include "../Generic/send_receive.h"

void * systeminfo(SSL* ssl)
{
    struct utsname systemInfo;
    uname(&systemInfo);

    // Get host information
    char hostname[256];
    gethostname(hostname, sizeof(hostname));

    // Get IP address
    struct ifaddrs *ifAddrStruct = NULL;
    getifaddrs(&ifAddrStruct);

    char ipAddresses[256] = ""; // Initialize an empty string to store IP addresses

    while (ifAddrStruct != NULL)
    {
        if (ifAddrStruct->ifa_addr != NULL && ifAddrStruct->ifa_addr->sa_family == AF_INET)
        {
            struct sockaddr_in *sa = (struct sockaddr_in *)ifAddrStruct->ifa_addr;
            char ipAddress[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &(sa->sin_addr), ipAddress, INET_ADDRSTRLEN);
            strcat(ipAddresses, ipAddress);
            strcat(ipAddresses, " ");
        }

        ifAddrStruct = ifAddrStruct->ifa_next;
    }

    // Get platform information
    char platformInfo[1024];
    sprintf(platformInfo, "System = {%s}\nRelease = {%s}\nVersion = {%s}\nArchitecture = {%s}\nIP Address = {%s}\n", systemInfo.sysname, systemInfo.release, systemInfo.version, systemInfo.machine, ipAddresses);
    freeifaddrs(ifAddrStruct);
    puts("Got system info");
    send_data(ssl, platformInfo);
}


