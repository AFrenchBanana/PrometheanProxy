package main

import (
	"fmt"
	"os"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "list_directory"
)

// LsCommand implements the shared.Command interface.
type LsCommand struct{}

// Execute is called when the command is run in the default context.
func (c *LsCommand) Execute(args []string) (string, error) {
	Logger.Log("LsCommand.Execute called (default context)")

	// Determine the directory path (default to current directory)
	path := "."
	if len(args) > 0 {
		path = args[0]
	}

	// Read directory entries
	entries, err := os.ReadDir(path)
	if err != nil {
		Logger.Error(fmt.Sprintf("Error reading directory: %v", err))
		return "", err
	}

	// Build output similar to "ls -al"
	output := ""
	for _, entry := range entries {
		info, err := entry.Info()
		if err != nil {
			continue // ...existing error handling...
		}
		// Format: permissions, links, owner, group, size, mod time, name
		line := fmt.Sprintf("%s %3d %8s %8s %8d %s %s",
			info.Mode().String(),
			1,
			"user", "group", // placeholders for owner and group
			info.Size(),
			info.ModTime().Format("Jan _2 15:04"),
			info.Name())
		output += line + "\n"
	}
	return output, nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *LsCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("LsCommand.ExecuteFromSession called")
	output, err := c.Execute(args)
	if err != nil {
		Logger.Error(fmt.Sprintf("Error in session context: %v", err))
		return "", err
	}
	return output, nil
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *LsCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("LsCommand.ExecuteFromBeacon called with data: %s", data))
	output, err := c.Execute(args)
	if err != nil {
		Logger.Error(fmt.Sprintf("Error in beacon context: %v", err))
		return "", err
	}
	return output, nil
}

// --- Main function for the plugin executable ---

func main() {

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &LsCommand{}},
		},
	})
}
