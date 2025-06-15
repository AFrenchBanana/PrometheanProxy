package main

import (
	"fmt"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "your_command_name" // Change this to a unique name for your command plugin
)

// Replace 'YourCommandImpl' with the specific name for your new command.
// This struct will implement the shared.Command interface.
type YourCommandImpl struct{}

// Execute is called when the command is run in the default context.
func (c *YourCommandImpl) Execute(args []string) (string, error) {
	Logger.Log("YourCommandImpl.Execute called (default context)")
	// TODO: Implement your command's core logic here.
	// 'args' will contain any arguments passed to the command.
	// Return the command's output as a string and any error encountered.
	return fmt.Sprintf("Hello from YourCommandImpl! Arguments: %v", args), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *YourCommandImpl) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("YourCommandImpl.ExecuteFromSession called")
	// Implement any logic needed to interface within the session context.
	// This should call Execute to allow similar behaviour betwween session and beacon contexts.

	output, err := c.Execute(args) // Example: Reuse default execute logic
	if err != nil {
		Logger.Error(fmt.Sprintf("Error in session context: %v", err))
		return "", err
	}
	return fmt.Sprintf(output), nil
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *YourCommandImpl) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("YourCommandImpl.ExecuteFromBeacon called with data: %s", data))
	// TODO: Implement logic specific to a beacon context.

	output, err := c.Execute(args) // Example: Reuse default execute logic
	if err != nil {
		Logger.Error(fmt.Sprintf("Error in beacon context: %v", err))
		return "", err
	}
	Logger.Log(fmt.Sprintf("Beacon data received: %s", data)) // Log to stderr
	return fmt.Sprintf(output), nil
}

// --- Main function for the plugin executable ---

func main() {

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &YourCommandImpl{}},
		},
	})
}
