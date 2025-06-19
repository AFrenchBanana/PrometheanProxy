package main

import (
	"fmt"
	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/shirou/gopsutil/v3/disk"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "diskusage"
)

// Replace 'YourCommandImpl' with the specific name for your new command.
// This struct will implement the shared.Command interface.
type DiskUsageCommand struct{}

// Execute is called when the command is run in the default context.
func (c *DiskUsageCommand) Execute(args []string) (string, error) {
	Logger.Log("DiskUsageCommand.Execute called")
	path := "/"
	if len(args) > 0 {
		path = args[0]
	}
	usage, err := disk.Usage(path)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf(
		"Path: %s\nTotal: %s\nUsed: %s (%.2f%%)\nFree: %s",
		usage.Path, formatBytes(usage.Total), formatBytes(usage.Used), usage.UsedPercent, formatBytes(usage.Free),
	), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *DiskUsageCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("DiskUsageCommand.ExecuteFromSession called")
	return c.Execute(args)
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *DiskUsageCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("DiskUsageCommand.ExecuteFromBeacon called with data: %s", data))
	return c.Execute(args)
}

func formatBytes(bytes uint64) string {
	const (
		KB = 1 << (10 * 1)
		MB = 1 << (10 * 2)
		GB = 1 << (10 * 3)
		TB = 1 << (10 * 4)
	)
	switch {
	case bytes >= TB:
		return fmt.Sprintf("%.2f TB", float64(bytes)/float64(TB))
	case bytes >= GB:
		return fmt.Sprintf("%.2f GB", float64(bytes)/float64(GB))
	case bytes >= MB:
		return fmt.Sprintf("%.2f MB", float64(bytes)/float64(MB))
	case bytes >= KB:
		return fmt.Sprintf("%.2f KB", float64(bytes)/float64(KB))
	default:
		return fmt.Sprintf("%d B", bytes)
	}
}

// --- Main function for the plugin executable ---
func main() {

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &DiskUsageCommand{}},
		},
	})
}
