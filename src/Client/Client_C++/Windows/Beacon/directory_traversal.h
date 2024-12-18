#include <string>
#include <json/json.h>  // Update include for jsoncpp

void getDirectoryContents(const std::string& path, Json::Value& result);

Json::Value convertToJSON(const std::string& rootPath);
