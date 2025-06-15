package shared

import (
	"fmt"
	"net/rpc"

	"github.com/hashicorp/go-plugin"
)

// Command is the interface that all dynamic commands must implement.
type Command interface {
	Execute(args []string) (string, error)
	ExecuteFromSession(args []string) (string, error)
	ExecuteFromBeacon(args []string, data string) (string, error) // 'data' for beacon-specific info
}

// --- RPC Client (Host Side) ---

// CommandRPCClient is the RPC client that the Host will use to call the Plugin.
type CommandRPCClient struct {
	client *rpc.Client
}

func (g *CommandRPCClient) Execute(args []string) (string, error) {
	var resp string
	err := g.client.Call("Plugin.Execute", args, &resp)
	if err != nil {
		return "", err
	}
	return resp, nil
}

func (g *CommandRPCClient) ExecuteFromSession(args []string) (string, error) {
	var resp string
	err := g.client.Call("Plugin.ExecuteFromSession", args, &resp)
	if err != nil {
		return "", err
	}
	return resp, nil
}

// Struct to pass arguments for ExecuteFromBeacon over RPC
type ExecuteFromBeaconArgs struct {
	Args []string
	Data string
}

func (g *CommandRPCClient) ExecuteFromBeacon(args []string, data string) (string, error) {
	var resp string
	err := g.client.Call("Plugin.ExecuteFromBeacon", ExecuteFromBeaconArgs{Args: args, Data: data}, &resp)
	if err != nil {
		return "", err
	}
	return resp, nil
}

// CommandRPCServer is the RPC server that the Plugin will implement for the Host to call.
type CommandRPCServer struct {
	Impl Command
}

func (s *CommandRPCServer) Execute(args []string, resp *string) error {
	var err error
	*resp, err = s.Impl.Execute(args)
	return err
}

func (s *CommandRPCServer) ExecuteFromSession(args []string, resp *string) error {
	var err error
	*resp, err = s.Impl.ExecuteFromSession(args) // Calls the plugin's actual implementation
	return err
}

func (s *CommandRPCServer) ExecuteFromBeacon(args ExecuteFromBeaconArgs, resp *string) error {
	var err error
	*resp, err = s.Impl.ExecuteFromBeacon(args.Args, args.Data) // Calls the plugin's actual implementation
	return err
}

// --- Plugin Handshake and Map ---

// CommandPlugin is the plugin.Plugin implementation.
type CommandPlugin struct {
	Impl Command
}

func (p *CommandPlugin) Server(*plugin.MuxBroker) (interface{}, error) {
	return &CommandRPCServer{Impl: p.Impl}, nil
}

func (p *CommandPlugin) Client(broker *plugin.MuxBroker, c *rpc.Client) (interface{}, error) {
	return &CommandRPCClient{client: c}, nil
}

// HandshakeConfigs are shared between the host and plugins to ensure compatibility.
var HandshakeConfig = plugin.HandshakeConfig{
	ProtocolVersion:  1,
	MagicCookieKey:   "BASIC_PLUGIN",
	MagicCookieValue: "hello",
}

// PluginMap is the map of plugins that the host will look for.
var PluginMap = make(map[string]plugin.Plugin)

// RegisterPlugin dynamically adds a new plugin to the PluginMap.
func RegisterPlugin(name string, pluginInstance plugin.Plugin) {
	PluginMap[name] = pluginInstance
	fmt.Printf("PluginMap contents after registration: %v\n", PluginMap)
}
