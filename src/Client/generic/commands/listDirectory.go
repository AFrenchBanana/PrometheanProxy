package commands

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/user"
	"src/Client/generic/logger"
	"strconv"
	"strings"
	"syscall"
)

// file represents metadata for a single file.
type file struct {
	Name         string
	Size         int64
	Permissions  string
	ModifiedTime string
	Owner        string
	Group        string
}

// directory represents a directory, containing its own metadata and a list of files.
type directory struct {
	Name        string
	Owner       string
	Group       string
	Permissions string
	Files       []file
}

// ListDirectory inspects a given directory path, populates the structs,
// and returns a formatted string representation.
func ListDirectory(path string) (directory, error) {
	path = strings.Trim(path, "\"")
	dirInfo, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return directory{}, fmt.Errorf("directory not found at '%s'", path)
		}
		return directory{}, fmt.Errorf("could not stat '%s': %v", path, err)
	}

	if !dirInfo.IsDir() {
		return directory{}, fmt.Errorf("path '%s' is not a directory", path)
	}

	entries, err := os.ReadDir(path)
	if err != nil {
		return directory{}, fmt.Errorf("could not read directory '%s': %v", path, err)
	}

	owner, group := getOwnerAndGroup(dirInfo)
	dirResult := directory{
		Name:        dirInfo.Name(),
		Permissions: dirInfo.Mode().String(),
		Owner:       owner,
		Group:       group,
		Files:       []file{},
	}

	for _, entry := range entries {
		// We only want to list files, not directories, within the main directory.
		if entry.IsDir() {
			continue
		}

		info, err := entry.Info()
		if err != nil {
			log.Printf("Warning: could not get info for '%s': %v", entry.Name(), err)
			continue
		}

		owner, group := getOwnerAndGroup(info)
		fileData := file{
			Name:         info.Name(),
			Size:         info.Size(),
			Permissions:  info.Mode().String(),
			ModifiedTime: info.ModTime().Format("Jan 02 15:04"),
			Owner:        owner,
			Group:        group,
		}
		dirResult.Files = append(dirResult.Files, fileData)
	}

	return dirResult, nil
}

// getOwnerAndGroup extracts user and group names from file info.
// This is platform-specific and works on Unix-like systems.
func getOwnerAndGroup(info os.FileInfo) (string, string) {
	// Default values
	ownerName := "n/a"
	groupName := "n/a"

	// Check if the underlying system data is available
	if stat, ok := info.Sys().(*syscall.Stat_t); ok {
		// Get User
		uidStr := strconv.Itoa(int(stat.Uid))
		if u, err := user.LookupId(uidStr); err == nil {
			ownerName = u.Username
		} else {
			ownerName = uidStr
		}

		// Get Group
		gidStr := strconv.Itoa(int(stat.Gid))
		if g, err := user.LookupGroupId(gidStr); err == nil {
			groupName = g.Name
		} else {
			groupName = gidStr
		}
	}
	return ownerName, groupName
}

type inputPayload struct {
	Path string `json:"path"`
}

func ListDirectoryBeacon(data string) string {

	var payload inputPayload
	if err := json.Unmarshal([]byte(data), &payload); err != nil {
		return fmt.Sprintf("invalid JSON: %v", err)
	}

	if payload.Path == "" {
		return fmt.Sprintf("missing or empty 'path' key in input JSON")
	}

	result := DirOutputAsString(payload.Path)
	return result
}

// DirOutputAsString takes a directory path as a string, retrieves its contents,
// and formats the information into a single, human-readable string.
func DirOutputAsString(dirPath string) string {
	logger.Log(fmt.Sprintf("Listing Directory %s", dirPath))

	dirInfo, err := ListDirectory(dirPath)
	if err != nil {
		logger.Error(fmt.Sprintf("error %v", err))
		return fmt.Sprintf("Error: %v", err)
	}

	var builder strings.Builder

	builder.WriteString(fmt.Sprintf("Listing for: %s\n", dirPath))
	builder.WriteString(strings.Repeat("-", 40) + "\n")

	header := fmt.Sprintf("%-12s %-12s %-12s %10s   %s\n",
		"Permissions", "Owner", "Group", "Size", "Name")
	builder.WriteString(header)

	if len(dirInfo.Files) == 0 {
		builder.WriteString("(Directory is empty)\n")
		return builder.String()
	}

	for _, f := range dirInfo.Files {
		builder.WriteString(fmt.Sprintf("%-12s %-12s %-12s %10d   %s\n",
			f.Permissions,
			f.Owner,
			f.Group,
			f.Size,
			f.Name,
		))
	}

	return builder.String()
}
