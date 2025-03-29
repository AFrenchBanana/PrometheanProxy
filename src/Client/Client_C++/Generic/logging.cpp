#include "logging.hpp"
#include <chrono>
#include <iomanip>
#include <sstream>

#ifdef DEBUG
Logger logger;

std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&in_time_t), "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

void Logger::log(const std::string& msg) {
    std::cout << "\033[32m[LOG] [" << getCurrentTimestamp() << "] " << msg << "\033[0m" << std::endl;
}

void Logger::warn(const std::string& msg) {
    std::cout << "\033[33m[WARN] [" << getCurrentTimestamp() << "] " << msg << "\033[0m" << std::endl;
}

void Logger::error(const std::string& msg) {
    std::cerr << "\033[31m[ERROR] [" << getCurrentTimestamp() << "] " << msg << "\033[0m" << std::endl;
}
#else
Logger logger;

void Logger::log(const std::string& msg) {}

void Logger::warn(const std::string& msg) {}

void Logger::error(const std::string& msg) {}
#endif


void surpressOutput() {
    struct NullBuffer : public std::streambuf {
        int overflow(int c) { return c; }
    } nullBuffer;
    std::ostream nullStream(&nullBuffer);
    std::cout.rdbuf(nullStream.rdbuf());
    std::cerr.rdbuf(nullStream.rdbuf());
}
