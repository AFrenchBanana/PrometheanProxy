package main

import (
	"encoding/json"
	"fmt"
	"io"
	"strings"

	"src/Client/dynamic/shared"
	"src/Client/generic/config"
	Logger "src/Client/generic/logger"

	hclog "github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

//go:embed obfuscate.json
var obfuscateJSON []byte

var pluginName string

const pluginKey = "netstat"

func init() {
	pluginName = pluginKey

	type entry struct {
		ObfuscatedName string `json:"obfuscation_name"`
	}
	var m map[string]entry
	if err := json.Unmarshal(obfuscateJSON, &m); err == nil {
		if e, ok := m[pluginKey]; ok {
			if n := strings.TrimSpace(e.ObfuscatedName); n != "" {
				pluginName = n
			}
		}
	}
}

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
	// Silence plugin logs unless in debug
	var plog hclog.Logger
	if config.IsDebug() {
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin.template", Level: hclog.Debug})
	} else {
		// hclog v1.x uses Trace/Debug/Info/Warn/Error; use NoLevel to silence, with Output discarded
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin.template", Level: hclog.NoLevel, Output: io.Discard})
	}

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &YourCommandImpl{}},
		},
		Logger: plog,
	})
}
