package session

import (
	"crypto/hmac"
	"crypto/sha512"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"runtime"
	"src/Client/generic/config"
	"src/Client/generic/logger"
	"time"

	"github.com/google/uuid"
)

const (
	ConnectionTimeout = 10
)

func computeHMAC(challenge, key []byte) string {
	h := hmac.New(sha512.New, key)
	h.Write(challenge)
	return hex.EncodeToString(h.Sum(nil))
}

// --- Main Handler ---

func SessionHandler() {
	if config.HMACKey == "" {
		logger.Error("HMAC key is required. Please provide it with the -hmac-key flag.")
		return
	}

	logger.Log("Session mode activated. Initiating connection and authentication.")
	tlsConfig := &tls.Config{InsecureSkipVerify: true}
	dialer := &net.Dialer{Timeout: ConnectionTimeout * time.Second}

	conn, err := tls.DialWithDialer(dialer, "tcp", config.SessionAddr, tlsConfig)
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to connect: %v", err))
		return
	}
	defer conn.Close()
	logger.Log(fmt.Sprintf("Successfully connected to %s", config.SessionAddr))

	// --- HMAC Challenge-Response Flow ---

	logger.Log("Waiting to receive challenge from server...")
	challenge, err := ReceiveData(conn)
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to receive challenge: %v", err))
		return
	}
	logger.Log(fmt.Sprintf("Received challenge: %s", string(challenge)))

	// 2. Compute the HMAC response using the shared key
	logger.Log("Computing HMAC response...")
	response := computeHMAC(challenge, []byte(config.HMACKey))
	logger.Log(fmt.Sprintf("Computed response: %s", response))

	// 3. Send the HMAC response back to the server
	logger.Log("Sending HMAC response to server...")
	err = SendData(conn, []byte(response))
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to send response: %v", err))
		return
	}

	logger.Log("Waiting for server authentication confirmation...")

	clientInfo := map[string]string{
		"Hostname": getHostname(),
		"OS":       getOS(),
		"ID":       getClientID(),
	}
	logger.Log("Gathering client information...")

	infoJSON, err := json.Marshal(clientInfo)
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to marshal client info: %v", err))
		return
	}

	logger.Log("Sending client info to server...")
	err = SendData(conn, infoJSON)
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to send client info: %v", err))
		return
	}

	_, _ = ReceiveData(conn) // place holder for the shark listener
}

// getHostname retrieves the system's hostname.
func getHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		return ""
	}
	return hostname
}

// getOS retrieves the operating system name.
func getOS() string {
	return runtime.GOOS
}

// getClientID retrieves a unique client ID (implement as needed).
func getClientID() string {
	return uuid.New().String()
}
