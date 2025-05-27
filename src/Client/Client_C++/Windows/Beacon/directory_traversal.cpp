#include <windows.h>
#include <vector>
#include <string>
#include <sstream> 
#include <iomanip>   
#include <json/json.h>
#include <curl/curl.h>
#include "../../Generic/logging.hpp"

// Helper function to convert a FILETIME structure to an ISO 8601 UTC string
std::string filetimeToISO8601(const FILETIME& ft) {
    SYSTEMTIME stUTC;
    if (!FileTimeToSystemTime(&ft, &stUTC)) {
        // Return a string indicating an error on failure
        return "Invalid Time";
    }

    std::ostringstream oss;
    oss << std::setfill('0')
        << std::setw(4) << stUTC.wYear << "-"
        << std::setw(2) << stUTC.wMonth << "-"
        << std::setw(2) << stUTC.wDay << "T"
        << std::setw(2) << stUTC.wHour << ":"
        << std::setw(2) << stUTC.wMinute << ":"
        << std::setw(2) << stUTC.wSecond << "Z";
    return oss.str();
}


// Function to traverse the directory recursively and create a detailed, compact JSON
void getDirectoryContents(const std::string& path, Json::Value& result) {
    WIN32_FIND_DATA findFileData;
    HANDLE hFind = FindFirstFile((path + "\\*").c_str(), &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        std::string errorMessage = "Error opening directory: " + path;
        logger.error(errorMessage);
        result["_errors"].append(errorMessage);
        return;
    }

    do {
        const std::string fileOrDir = findFileData.cFileName;
        if (fileOrDir != "." && fileOrDir != "..") {
            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                // For a directory, the directory name becomes the key.
                getDirectoryContents(path + "\\" + fileOrDir, result[fileOrDir]);
            } else {
                // For a file, create a detailed JSON object for it.
                Json::Value fileDetails;

                // 1. Calculate the 64-bit file size
                ULARGE_INTEGER fileSize;
                fileSize.LowPart = findFileData.nFileSizeLow;
                fileSize.HighPart = findFileData.nFileSizeHigh;
                fileDetails["size"] = static_cast<Json::UInt64>(fileSize.QuadPart);

                // 2. Convert timestamps to ISO 8601 strings
                fileDetails["lastModified"] = filetimeToISO8601(findFileData.ftLastWriteTime);
                fileDetails["created"] = filetimeToISO8601(findFileData.ftCreationTime);
                
                // 3. Add other info like attributes
                fileDetails["attributes"] = findFileData.dwFileAttributes;

                // 4. Assign the details object as the value for the file's key
                result[fileOrDir] = fileDetails;
            }
        }
    } while (FindNextFile(hFind, &findFileData));

    DWORD dwError = GetLastError();
    if (dwError != ERROR_NO_MORE_FILES) {
        std::string errorMessage = "Error reading directory contents in path: " + path;
        logger.error(errorMessage);
        result["_errors"].append(errorMessage);
    }

    if (!FindClose(hFind)) {
        std::string errorMessage = "Error closing directory handle for path: " + path;
        logger.error(errorMessage);
        result["_errors"].append(errorMessage);
    }
}

// Convert the directory list to the compact JSON format
Json::Value convertToJSON(const std::string& rootPath) {
    logger.log("Starting directory traversal for root path: " + rootPath);
    Json::Value root;
    getDirectoryContents(rootPath, root);
    logger.log("Completed directory traversal for root path: " + rootPath);
    return root;
}