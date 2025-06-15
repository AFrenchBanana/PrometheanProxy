package commands

// import (
// 	"encoding/json"
// 	"fmt"
// 	"os"
// 	"path/filepath"
// 	"src/Client/generic/logger"
// 	"time"
// )

// type FileDetails struct {
// 	Size         int64  `json:"size"`
// 	LastModified string `json:"lastModified"`
// 	Attributes   string `json:"attributes"`
// }

// func getDirectoryContents(path string, result map[string]interface{}) {
// 	logger.Log(fmt.Sprintf("Reading directory: %s", path))
// 	entries, err := os.ReadDir(path)
// 	if err != nil {
// 		logger.Error(fmt.Sprintf("Error opening directory: %s, %v", path, err))
// 		if _, ok := result["_errors"]; !ok {
// 			result["_errors"] = []string{}
// 		}
// 		result["_errors"] = append(result["_errors"].([]string), fmt.Sprintf("Error opening directory: %s", path))
// 		return
// 	}

// 	for _, entry := range entries {
// 		fullPath := filepath.Join(path, entry.Name())
// 		logger.Log(fmt.Sprintf("Processing entry: %s", fullPath))
// 		if entry.IsDir() {
// 			logger.Log(fmt.Sprintf("Found directory: %s", fullPath))
// 			// For a directory, the directory name becomes the key.
// 			// Create a new map for the subdirectory and make a recursive call.
// 			subDirContents := make(map[string]interface{})
// 			logger.Log(fmt.Sprintf("Recursively getting contents of directory: %s", fullPath))
// 			getDirectoryContents(fullPath, subDirContents)
// 			logger.Log(fmt.Sprintf("Completed getting contents of directory: %s", fullPath))
// 			result[entry.Name()] = subDirContents
// 		} else {
// 			logger.Log(fmt.Sprintf("Found file: %s", fullPath))
// 			// For a file, get its detailed information using the portable os.FileInfo.
// 			fileInfo, err := entry.Info()
// 			logger.Log(fmt.Sprintf("Getting info for file: %s", fullPath))
// 			if err != nil {
// 				logger.Error(fmt.Sprintf("Error getting info for file: %s, %v", fullPath, err))
// 				if _, ok := result["_errors"]; !ok {
// 					logger.Error(fmt.Sprintf("Error getting info for file: %s, %v", fullPath, err))
// 					result["_errors"] = []string{}
// 				}
// 				result["_errors"] = append(result["_errors"].([]string), fmt.Sprintf("Error getting info for file: %s", fullPath))
// 				continue
// 			}

// 			// 1. Get the file size
// 			size := fileInfo.Size()
// 			logger.Log(fmt.Sprintf("File size for %s: %d bytes", fullPath, size))

// 			// 2. Format last modified time to ISO 8601 UTC (RFC3339)
// 			lastModified := fileInfo.ModTime().UTC().Format(time.RFC3339)
// 			logger.Log(fmt.Sprintf("Last modified time for %s: %s", fullPath, lastModified))
// 			// 3. Get file mode/attributes as a string (e.g., "-rw-r--r--")
// 			attributes := fileInfo.Mode().String()
// 			logger.Log(fmt.Sprintf("File attributes for %s: %s", fullPath, attributes))
// 			// 4. Assign the details struct as the value for the file's key
// 			result[entry.Name()] = FileDetails{
// 				Size:         size,
// 				LastModified: lastModified,
// 				Attributes:   attributes,
// 			}
// 		}
// 	}
// }

// func DirectoryTraversal(rootPath string) string {
// 	var err error
// 	if rootPath == "" {
// 		logger.Warn("Root path is empty")
// 		rootPath, err = os.Getwd()
// 		if err != nil {
// 			logger.Error(fmt.Sprintf("Error getting current working directory: %v", err))
// 			return fmt.Sprintf("No dir supplied, error getting current working directory: %v", err)
// 		}
// 	}
// 	logger.Log(fmt.Sprintf("Starting directory traversal for root path: %s", rootPath))

// 	// The root object that will hold the entire directory structure
// 	root := make(map[string]interface{})

// 	getDirectoryContents(rootPath, root)

// 	logger.Log(fmt.Sprintf("Completed directory traversal for root path: %s", rootPath))

// 	// Marshal the map into a nicely indented JSON string
// 	jsonData, err := json.MarshalIndent(root, "", "  ")
// 	if err != nil {
// 		logger.Error(fmt.Sprintf("Error marshalling JSON: %v", err))
// 		return fmt.Sprintf("Error marshalling JSON: %v", err)
// 	}

// 	return string(jsonData)
// }

// func DirectoryTraversalBeacon(data string) string {

// 	var directories inputPayload
// 	if err := json.Unmarshal([]byte(data), &directories); err != nil {
// 		return fmt.Sprintf("invalid JSON: %v", err)
// 	}

// 	if directories.Path == "" {
// 		return fmt.Sprintf("missing or empty 'path' key in input JSON")
// 	}

// 	result := DirOutputAsString(directories.Path)
// 	return result
// }
