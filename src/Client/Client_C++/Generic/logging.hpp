#ifndef LOGGING_HPP
#define LOGGING_HPP

#include <string>
#include <iostream>

class Logger {
public:
    void log(const std::string& msg);
    void warn(const std::string& msg);
    void error(const std::string& msg);
    void operator()(const std::string& msg) { log(msg); }
};

extern Logger logger;
void surpressOutput();

#endif
