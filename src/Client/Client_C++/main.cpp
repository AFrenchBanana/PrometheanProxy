#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <unistd.h>
#include <ifaddrs.h>
#include <arpa/inet.h>

class Client {
public:
    static std::tuple<int, std::string, int> httpConnection(const std::string& address) {
        char hostname[1024];
        if (gethostname(hostname, sizeof(hostname)) != 0) {
            throw std::runtime_error("Failed to get hostname");
        }
        std::string hostname;
        
        char ip_buffer[INET_ADDRSTRLEN];
        struct ifaddrs *ifap, *ifa;
        struct sockaddr_in *sa;

        if (getifaddrs(&ifap) == 0) {
            for (ifa = ifap; ifa != nullptr; ifa = ifa->ifa_next) {
            if (ifa->ifa_addr->sa_family == AF_INET) {
                sa = (struct sockaddr_in *) ifa->ifa_addr;
                inet_ntop(AF_INET, &(sa->sin_addr), ip_buffer, INET_ADDRSTRLEN);
                if (std::string(ifa->ifa_name) == "eth0") { // Assuming eth0 is the interface you want
                break;
                }
            }
            }
            freeifaddrs(ifap);
        } else {
            throw std::runtime_error("Failed to get IP address");
        }

        std::string IPAddress(ip_buffer);

        std::string url = "http://" + address + "/connection?name=" + hostname + "&os=" + "C++" + "&address=" + IPAddress;
        std::cout << "Request URL: " << url << std::endl;

        // Call the getRequest method
        auto [response_code, response_body, response_url] = getRequest(url);

        try {
            if (response_code == 200) {
                int timer = 20; 
                std::string ID = "12345";
                int jitter = 5; 
                return std::make_tuple(timer, ID, jitter);
            } else {
                throw std::runtime_error("Failed to connect to server: " + std::to_string(response_code) + " " + response_body);
            }
        } catch (const std::exception& e) {
            std::cerr << "Exception: " << e.what() << std::endl;
            throw; // rethrow the exception after logging
        }
    }

private:
    static std::tuple<int, std::string, std::string> getRequest(const std::string& url) {
        CURL* curl;
        CURLcode res;
        long response_code;
        std::string response_body;

        curl_global_init(CURL_GLOBAL_DEFAULT);
        curl = curl_easy_init();
        if(curl) {
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_body);
            res = curl_easy_perform(curl);
            if(res != CURLE_OK) {
                throw std::runtime_error("curl_easy_perform() failed: " + std::string(curl_easy_strerror(res)));
            }
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
            curl_easy_cleanup(curl);
        }
        curl_global_cleanup();
        return std::make_tuple(response_code, response_body, url);
    }

    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s) {
        size_t newLength = size * nmemb;
        try {
            s->append((char*)contents, newLength);
        } catch(std::bad_alloc &e) {
            // Handle memory problem
            return 0;
        }
        return newLength;
    }
};

int main() {
    try {
        auto result = Client::httpConnection("127.0.0.1");
        std::cout << "Timer: " << std::get<0>(result) << ", ID: " << std::get<1>(result) << ", Jitter: " << std::get<2>(result) << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to establish HTTP connection: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}