#include <string>
#include <iostream>

#ifdef DEBUG
void logger(std::string message){
    std::cout << "Log: " << message << std::endl;
}

void log_error(std::string message){
    std::cout << "Error: " << message << std::endl;
}
#else
void logger(std::string /*message*/){
    // Logging disabled in non-debug builds.
}

void log_error(std::string /*message*/){
    // Logging disabled in non-debug builds.
}
#endif