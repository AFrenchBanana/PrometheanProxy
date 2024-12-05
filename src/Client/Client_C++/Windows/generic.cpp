#include <winsock2.h>
#include <iphlpapi.h>
#include <iostream>
#include <vector>

#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "Iphlpapi.lib")


// Get the IP addresses of the local machine and return them as a vector of strings
std::vector<std::string> getIPAddresses() {
    std::vector<std::string> ipAddresses;
    PIP_ADAPTER_INFO pAdapterInfo;
    PIP_ADAPTER_INFO pAdapter = NULL;
    DWORD dwRetVal = 0;
    ULONG ulOutBufLen = sizeof(IP_ADAPTER_INFO);

    pAdapterInfo = (IP_ADAPTER_INFO *)malloc(sizeof(IP_ADAPTER_INFO));
    if (pAdapterInfo == NULL) {
        std::cerr << "Error allocating memory needed to call GetAdaptersinfo\n";
        return ipAddresses;
    }

    if (GetAdaptersInfo(pAdapterInfo, &ulOutBufLen) == ERROR_BUFFER_OVERFLOW) {
        free(pAdapterInfo);
        pAdapterInfo = (IP_ADAPTER_INFO *)malloc(ulOutBufLen);
        if (pAdapterInfo == NULL) {
            std::cerr << "Error allocating memory needed to call GetAdaptersinfo\n";
            return ipAddresses;
        }
    }

    if ((dwRetVal = GetAdaptersInfo(pAdapterInfo, &ulOutBufLen)) == NO_ERROR) {
        pAdapter = pAdapterInfo;
        while (pAdapter) {
            ipAddresses.push_back(pAdapter->IpAddressList.IpAddress.String);
            pAdapter = pAdapter->Next;
        }
    } else {
        std::cerr << "GetAdaptersInfo failed with error: " << dwRetVal << "\n";
    }

    if (pAdapterInfo)
        free(pAdapterInfo);

    return ipAddresses;
}