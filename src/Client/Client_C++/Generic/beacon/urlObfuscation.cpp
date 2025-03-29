#include <string>
#include <vector>
#include <random>
#include <sstream>

#include "../config.hpp"
#include "../logging.hpp"

std::vector<std::string> adDownloadUrlParams = {
    "ad_id",
    "ad_group",
    "ad_campaign",
    "ad_creative",
    "ad_position",
    "ad_placement",
    "ad_network",
    "ad_click_id",
    "gcladid",
    "fbclidad",
    "ad_format",
    "ad_size",
    "ad_type",
    "ad_language",
    "ad_region"
};


std::vector<std::string> webDirectories = {
    "about",
    "about-us",
    "account",
    "admin",
    "ads",
    "api",
    "app",
    "archive",
    "assets",
    "auth",
    "backup",
    "blog",
    "booking",
    "browse",
    "build",
    "cache",
    "calendar",
    "cart",
    "catalog",
    "category",
    "cgi-bin",
    "checkout",
    "client",
    "comments",
    "community",
    "config",
    "contact",
    "control-panel",
    "css",
    "dashboard",
    "data",
    "db",
    "debug",
    "default",
    "demo",
    "deploy",
    "dev",
    "docs",
    "download",
    "edit",
    "error",
    "events",
    "example",
    "examples",
    "export",
    "extensions",
    "faq",
    "features",
    "feed",
    "files",
    "forum",
    "gallery",
    "graphics",
    "guestbook",
    "help",
    "history",
    "home",
    "icons",
    "images",
    "img",
    "import",
    "includes",
    "info",
    "install",
    "inventory",
    "invoices",
    "js",
    "json",
    "lang",
    "language",
    "layout",
    "lib",
    "license",
    "links",
    "list",
    "live",
    "local",
    "locale",
    "login",
    "logout",
    "logs",
    "mail",
    "manage",
    "map",
    "media",
    "members",
    "messages",
    "mobile",
    "modules",
    "news",
    "notes",
    "notifications",
    "offline",
    "order",
    "orders",
    "pages",
    "partners",
    "password",
    "pay",
    "payment",
    "photos",
    "plugins",
    "policy",
    "portal",
    "portfolio",
    "posts",
    "preferences",
    "pricing",
    "privacy",
    "profile",
    "projects",
    "public",
    "purchase",
    "queries",
    "query",
    "ratings",
    "register",
    "reports",
    "resources",
    "reviews",
    "rss",
    "sales",
    "scripts",
    "search",
    "secure",
    "security",
    "server",
    "services",
    "settings",
    "shop",
    "signin",
    "signup",
    "site",
    "sitemap",
    "src",
    "static",
    "stats",
    "status",
    "store",
    "style",
    "styles",
    "support",
    "survey",
    "sync",
    "system",
    "tags",
    "tasks",
    "team",
    "terms",
    "test",
    "theme",
    "themes",
    "tmp",
    "tools",
    "tracking",
    "training",
    "translations",
    "uploads",
    "user",
    "users",
    "util",
    "utilities",
    "vendor",
    "videos",
    "web",
    "webhooks",
    "widgets",
    "wiki",
    "work",
    "xml",
    "yaml"
};

std::string generateUUID() {
    logger.log("generateUUID: Start");
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 15);
    std::uniform_int_distribution<> dis2(8, 11);

    std::stringstream ss;
    ss << std::hex;
    for (int i = 0; i < 8; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 4; i++) ss << dis(gen);
    ss << "-4";
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    ss << dis2(gen);
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 12; i++) ss << dis(gen);

    std::string uuid = ss.str();
    logger.log("generateUUID: Generated UUID: " + uuid);
    return uuid;
}

std::string getRandomElement(const std::vector<std::string>& vec) {
    if (vec.empty()) {
        logger.error("getRandomElement: Provided vector is empty");
        return "";
    }
    logger.log("getRandomElement: Selecting random element");
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, vec.size() - 1);
    std::string element = vec[dis(gen)];
    logger.log("getRandomElement: Selected element: " + element);
    return element;
}

std::string generateConnectionURL() {
    logger.log("generateConnectionURL: Start");
    std::string part1 = getRandomElement(webDirectories);
    std::string part2 = getRandomElement(webDirectories);
    std::string adParam = getRandomElement(adDownloadUrlParams);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 10);
    int version = dis(gen);
    std::string uuid = generateUUID();
    
    std::stringstream url;
    url << URL << "/" << part1 << "/" << part2 << "/" << adParam << "/api/v" << version << "?user=" << uuid;
    std::string connectionUrl = url.str();
    logger.log("generateConnectionURL: Generated Connection URL: " + connectionUrl);
    return connectionUrl;
}

std::string generateReconnectURL() {
    logger.log("generateReconnectURL: Start");
    std::string part1 = getRandomElement(webDirectories);
    std::string adParam = getRandomElement(adDownloadUrlParams);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 10);
    int version = dis(gen);
    std::string uuid = generateUUID();
    
    std::stringstream url;
    url << URL << "/" << part1 << "/"  << adParam << "/getLatest" << "?token=" << uuid;
    std::string reconnectUrl = url.str();
    logger.log("generateReconnectURL: Generated Reconnect URL: " + reconnectUrl);
    return reconnectUrl;
}

std::string generateBeaconURL() { 
    logger.log("generateBeaconURL: Start");
    std::string part1 = getRandomElement(webDirectories);
    std::string part2 = getRandomElement(webDirectories);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 10);
    int version = dis(gen);
    
    std::stringstream url;
    url << URL << "/checkUpdates/" << part1 << "/"  << part2 << "?session=" << ID << "&v=" << version;
    std::string beaconUrl = url.str();
    logger.log("generateBeaconURL: Generated Beacon URL: " + beaconUrl);
    return beaconUrl;
}

std::string generateResponse() { 
    logger.log("generateResponse: Start");
    std::string part1 = getRandomElement(webDirectories);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 10);
    int version = dis(gen);
    bool executed = dis(gen) > 5;
    std::string executedStr = executed ? "true" : "false";
    std::string uuid = generateUUID();
    
    std::stringstream url;
    url << URL << "/updateReport/" << part1 << "/"  << "api/v" << version << "?Executed=" << executedStr << "&responseID=" << uuid; 
    std::string responseUrl = url.str();
    logger.log("generateResponse: Generated Response URL: " + responseUrl);
    return responseUrl;
}