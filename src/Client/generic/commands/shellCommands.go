package commands

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
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
