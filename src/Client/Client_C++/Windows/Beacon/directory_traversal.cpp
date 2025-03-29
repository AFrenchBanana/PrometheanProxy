#include <windows.h>
#include <vector>
#include <string>
#include <json/json.h>
#include <curl/curl.h>
#include "../../Generic/logging.hpp"

// Function to traverse the directory recursively
void getDirectoryContents(const std::string& path, Json::Value& result) {
    WIN32_FIND_DATA findFileData;
    HANDLE hFind = FindFirstFile((path + "\\*").c_str(), &findFileData);

    if (!result.isMember("directories")) {
        result["directories"] = Json::arrayValue;
    }
    if (!result.isMember("files")) {
        result["files"] = Json::arrayValue;
    }

    if (hFind == INVALID_HANDLE_VALUE) {
        // Collect error instead of printing
        std::string errorMessage = "Error opening directory: " + path;
        result["errors"].append(errorMessage);
        logger.error(errorMessage);
        return;
    }

    do {
        const std::string fileOrDir = findFileData.cFileName;
        if (fileOrDir != "." && fileOrDir != "..") {
            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                // Recurse into subdirectory
                Json::Value subdir;
                getDirectoryContents(path + "\\" + fileOrDir, subdir);
                Json::Value dirEntry;
                dirEntry["name"] = fileOrDir;
                dirEntry["contents"] = subdir;
                result["directories"].append(dirEntry);
            } else {
                result["files"].append(fileOrDir);
            }
        }
    } while (FindNextFile(hFind, &findFileData));

    if (!FindClose(hFind)) {
        logger.error("Error closing directory handle for path: " + path);
    }
}

// Convert the directory list to JSON
Json::Value convertToJSON(const std::string& rootPath) {
    logger.log("Starting directory traversal for root path: " + rootPath);
    Json::Value root;
    getDirectoryContents(rootPath, root);
    logger.log("Completed directory traversal for root path: " + rootPath);
    return root;
}