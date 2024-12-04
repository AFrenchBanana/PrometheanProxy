#include <string>
#include <iostream>

std::string command_handler(const std::string& command, const std::string& uuid);
std::string executeShellCommand(const char* cmd);
std::string getSystemInfo();
std::string getMacAddress();
