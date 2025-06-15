package main

import (
	"fmt"
	"net"
	"strings"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	gopsutilNet "github.com/shirou/gopsutil/v3/net"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "netstat"
)

// Replace 'YourCommandImpl' with the specific name for your new command.
// This struct will implement the shared.Command interface.
type YourCommandImpl struct{}

// Execute is called when the command is run in the default context.
func (c *YourCommandImpl) Execute(args []string) (string, error) {
	Logger.Log("YourCommandImpl.Execute called (default context)")
	var sb strings.Builder

	// Interface details (like `ip -a`)
	sb.WriteString("Interface Details:\n")
	ifaces, err := net.Interfaces()
	if err != nil {
		return "", fmt.Errorf("cannot list interfaces: %v", err)
	}
	for _, iface := range ifaces {
		sb.WriteString(fmt.Sprintf("Name: %s, MAC: %s, Flags: %v\n", iface.Name, iface.HardwareAddr, iface.Flags))
		addrs, _ := iface.Addrs()
		for _, addr := range addrs {
			sb.WriteString(fmt.Sprintf("  Addr: %s\n", addr.String()))
		}
	}

	// Network connections (like `netstat -aon`)
	sb.WriteString("\nNetwork Connections:\n")
	conns, err := gopsutilNet.Connections("all")
	if err != nil {
		return "", fmt.Errorf("cannot list connections: %v", err)
	}
	for _, cstat := range conns {
		sb.WriteString(fmt.Sprintf(
			"%s %s:%d -> %s:%d %s PID:%d\n",
			cstat.Type,
			cstat.Laddr.IP, cstat.Laddr.Port,
			cstat.Raddr.IP, cstat.Raddr.Port,
			cstat.Status,
			cstat.Pid,
		))
	}

	return sb.String(), nil
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
