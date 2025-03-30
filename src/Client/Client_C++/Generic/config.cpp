#include "config.hpp"
#include "logging.hpp"

#ifdef __unix__
    #ifdef DEBUG
        std::string OS = "Linux (DEBUG)";
    #else
        std::string OS = "Linux";
    #endif
#elif defined(_WIN32)
    #ifdef DEBUG
        std::string OS = "Windows (DEBUG)";
    #else
        std::string OS = "Windows";
    #endif
#else
    #ifdef DEBUG
        std::string OS = "Unknown (DEBUG)";
    #else
        std::string OS = "Unknown";
    #endif
#endif

const std::string SOCKET_ADDR = "127.0.0.1";
const int SOCKET_PORT = 2000;

const std::string URL = "http://" + SOCKET_ADDR + ":8000";
std::string ID = "";

int JITTER = -1;
int TIMER = -1;

