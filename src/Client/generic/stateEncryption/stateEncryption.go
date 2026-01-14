package stateEncryption

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"runtime"
	"time"

	"golang.org/x/crypto/pbkdf2"
)

const (
	// KeySize for AES-256
	KeySize = 32
	// NonceSize for GCM
	NonceSize = 12
	// SaltSize for PBKDF2
	SaltSize = 32
	// PBKDF2 iterations
	PBKDF2Iterations = 100000
)

var debugMode bool

func init() {
	// Check if debug mode is enabled via environment variable
	debugMode = os.Getenv("DEBUG") != "" || os.Getenv("CLIENT_DEBUG") != ""
}

// log prints debug messages if debug mode is enabled
func log(format string, args ...interface{}) {
	if debugMode {
		timestamp := time.Now().Format("2006-01-02 15:04:05")
		msg := fmt.Sprintf(format, args...)
		fmt.Printf("\033[32m[LOG] [%s] [StateEncryption] %s\033[0m\n", timestamp, msg)
	}
}

// logError prints error messages if debug mode is enabled
func logError(format string, args ...interface{}) {
	if debugMode {
		timestamp := time.Now().Format("2006-01-02 15:04:05")
		msg := fmt.Sprintf(format, args...)
		fmt.Fprintf(os.Stderr, "\033[31m[ERROR] [%s] [StateEncryption] %s\033[0m\n", timestamp, msg)
	}
}

// ClientState holds all sensitive client data that needs encryption
type ClientState struct {
	ID          string            `json:"id"`
	Jitter      float64           `json:"jitter"`
	Timer       float64           `json:"timer"`
	URL         string            `json:"url"`
	SessionAddr string            `json:"session_addr"`
	HMACKey     string            `json:"hmac_key"`
	Hostname    string            `json:"hostname"`
	OS          string            `json:"os"`
	ClientID    string            `json:"client_id"`
	Metadata    map[string]string `json:"metadata"`
}

// EncryptedState holds encrypted data and crypto parameters
type EncryptedState struct {
	Ciphertext []byte `json:"ciphertext"`
	Nonce      []byte `json:"nonce"`
	Salt       []byte `json:"salt"`
	Timestamp  int64  `json:"timestamp"`
}

var (
	// currentState holds decrypted state when active
	currentState *ClientState
	// encryptedState holds encrypted state when idle
	encryptedState *EncryptedState
	// masterKey is derived from system entropy
	masterKey []byte
	// isEncrypted tracks current encryption state
	isEncrypted bool
)

// init initializes the state encryption system
func init() {
	log("Initializing state encryption module")
	isEncrypted = false
	currentState = nil
	encryptedState = nil
	log("State encryption module initialized")
}

// GenerateMasterKey creates a master key from system entropy
func GenerateMasterKey() error {
	log("Generating master key from system entropy")

	// Generate random salt
	salt := make([]byte, SaltSize)
	if _, err := io.ReadFull(rand.Reader, salt); err != nil {
		logError("Failed to generate salt: %v", err)
		return fmt.Errorf("failed to generate salt: %w", err)
	}
	log("Generated salt of size %d bytes", len(salt))

	// Gather system entropy (timestamp, memory stats, random bytes)
	entropy := gatherSystemEntropy()
	log("Gathered system entropy of size %d bytes", len(entropy))

	// Derive key using PBKDF2
	masterKey = pbkdf2.Key(entropy, salt, PBKDF2Iterations, KeySize, sha256.New)
	log("Master key derived using PBKDF2 with %d iterations", PBKDF2Iterations)

	// Clear entropy from memory
	for i := range entropy {
		entropy[i] = 0
	}
	log("Cleared entropy from memory")

	return nil
}

// gatherSystemEntropy collects system-specific entropy
func gatherSystemEntropy() []byte {
	log("Gathering system entropy")

	var entropy []byte

	// Add timestamp
	timestamp := time.Now().UnixNano()
	timestampBytes := []byte(fmt.Sprintf("%d", timestamp))
	entropy = append(entropy, timestampBytes...)
	log("Added timestamp entropy: %d", timestamp)

	// Add memory stats
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	memBytes := []byte(fmt.Sprintf("%d%d%d", m.Alloc, m.TotalAlloc, m.Sys))
	entropy = append(entropy, memBytes...)
	log("Added memory stats entropy (Alloc: %d, TotalAlloc: %d, Sys: %d)", m.Alloc, m.TotalAlloc, m.Sys)

	// Add random bytes
	randomBytes := make([]byte, 64)
	if _, err := io.ReadFull(rand.Reader, randomBytes); err == nil {
		entropy = append(entropy, randomBytes...)
		log("Added %d random bytes to entropy", len(randomBytes))
	} else {
		logError("Failed to read random bytes: %v", err)
	}

	log("Total entropy size: %d bytes", len(entropy))
	return entropy
}

// EncryptState encrypts the current client state and clears unencrypted data
func EncryptState(state *ClientState) error {
	log("========== BEGIN ENCRYPTION PROCESS ==========")
	log("Current encryption state: %v", isEncrypted)

	if isEncrypted {
		log("State is already encrypted, skipping")
		return nil
	}

	if state == nil {
		logError("Cannot encrypt nil state")
		return fmt.Errorf("state is nil")
	}

	log("State to encrypt - ID: %s, URL: %s, SessionAddr: %s", state.ID, state.URL, state.SessionAddr)

	// Generate master key if not already generated
	if masterKey == nil {
		log("Master key not found, generating new master key")
		if err := GenerateMasterKey(); err != nil {
			logError("Failed to generate master key: %v", err)
			return err
		}
	} else {
		log("Using existing master key")
	}

	// Marshal state to JSON
	log("Marshaling state to JSON")
	plaintext, err := json.Marshal(state)
	if err != nil {
		logError("Failed to marshal state: %v", err)
		return fmt.Errorf("failed to marshal state: %w", err)
	}
	log("State marshaled to JSON, size: %d bytes", len(plaintext))

	// Create cipher block
	log("Creating AES cipher block")
	block, err := aes.NewCipher(masterKey)
	if err != nil {
		logError("Failed to create cipher: %v", err)
		return fmt.Errorf("failed to create cipher: %w", err)
	}
	log("AES cipher block created successfully")

	// Create GCM mode
	log("Creating GCM cipher mode")
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		logError("Failed to create GCM: %v", err)
		return fmt.Errorf("failed to create GCM: %w", err)
	}
	log("GCM cipher mode created successfully")

	// Generate nonce
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		logError("Failed to generate nonce: %v", err)
		return fmt.Errorf("failed to generate nonce: %w", err)
	}
	log("Nonce generated, size: %d bytes", len(nonce))

	// Generate salt for this encryption
	salt := make([]byte, SaltSize)
	if _, err := io.ReadFull(rand.Reader, salt); err != nil {
		logError("Failed to generate salt: %v", err)
		return fmt.Errorf("failed to generate salt: %w", err)
	}
	log("Salt generated, size: %d bytes", len(salt))

	// Encrypt data
	log("Encrypting plaintext with AES-GCM")
	ciphertext := gcm.Seal(nil, nonce, plaintext, nil)
	log("Encryption complete, ciphertext size: %d bytes", len(ciphertext))

	// Store encrypted state
	encryptedState = &EncryptedState{
		Ciphertext: ciphertext,
		Nonce:      nonce,
		Salt:       salt,
		Timestamp:  time.Now().Unix(),
	}
	log("Encrypted state stored with timestamp: %d", encryptedState.Timestamp)

	// Clear plaintext from memory
	log("Clearing plaintext from memory")
	for i := range plaintext {
		plaintext[i] = 0
	}
	log("Plaintext cleared")

	// Clear the current state
	log("Clearing current state object")
	clearState(state)
	currentState = nil
	log("Current state cleared and set to nil")

	// Force garbage collection
	log("Forcing garbage collection")
	runtime.GC()
	log("Garbage collection completed")

	isEncrypted = true
	log("Encryption state flag set to true")
	log("========== ENCRYPTION PROCESS COMPLETE ==========")

	return nil
}

// DecryptState decrypts the encrypted state and returns a new ClientState
func DecryptState() (*ClientState, error) {
	log("========== BEGIN DECRYPTION PROCESS ==========")
	log("Current encryption state: %v", isEncrypted)

	if !isEncrypted {
		log("State is not encrypted, returning current state")
		if currentState != nil {
			log("Returning existing current state")
			return currentState, nil
		}
		logError("No encrypted or current state available")
		return nil, fmt.Errorf("no encrypted state available")
	}

	if encryptedState == nil {
		logError("Encrypted state is nil")
		return nil, fmt.Errorf("encrypted state is nil")
	}

	log("Encrypted state timestamp: %d", encryptedState.Timestamp)
	log("Ciphertext size: %d bytes", len(encryptedState.Ciphertext))
	log("Nonce size: %d bytes", len(encryptedState.Nonce))

	if masterKey == nil {
		logError("Master key is nil, cannot decrypt")
		return nil, fmt.Errorf("master key is nil")
	}
	log("Master key is available")

	// Create cipher block
	log("Creating AES cipher block for decryption")
	block, err := aes.NewCipher(masterKey)
	if err != nil {
		logError("Failed to create cipher: %v", err)
		return nil, fmt.Errorf("failed to create cipher: %w", err)
	}
	log("AES cipher block created successfully")

	// Create GCM mode
	log("Creating GCM cipher mode for decryption")
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		logError("Failed to create GCM: %v", err)
		return nil, fmt.Errorf("failed to create GCM: %w", err)
	}
	log("GCM cipher mode created successfully")

	// Decrypt data
	log("Decrypting ciphertext with AES-GCM")
	plaintext, err := gcm.Open(nil, encryptedState.Nonce, encryptedState.Ciphertext, nil)
	if err != nil {
		logError("Failed to decrypt: %v", err)
		return nil, fmt.Errorf("failed to decrypt: %w", err)
	}
	log("Decryption complete, plaintext size: %d bytes", len(plaintext))

	// Unmarshal state
	log("Unmarshaling decrypted JSON to state object")
	var state ClientState
	if err := json.Unmarshal(plaintext, &state); err != nil {
		logError("Failed to unmarshal state: %v", err)
		// Clear plaintext before returning
		for i := range plaintext {
			plaintext[i] = 0
		}
		return nil, fmt.Errorf("failed to unmarshal state: %w", err)
	}
	log("State unmarshaled - ID: %s, URL: %s, SessionAddr: %s", state.ID, state.URL, state.SessionAddr)

	// Clear plaintext from memory
	log("Clearing plaintext from memory")
	for i := range plaintext {
		plaintext[i] = 0
	}
	log("Plaintext cleared")

	// Clear encrypted state
	log("Clearing encrypted state from memory")
	clearEncryptedState(encryptedState)
	encryptedState = nil
	log("Encrypted state cleared and set to nil")

	// Set current state
	currentState = &state
	log("Current state updated with decrypted data")

	isEncrypted = false
	log("Encryption state flag set to false")
	log("========== DECRYPTION PROCESS COMPLETE ==========")

	return currentState, nil
}

// clearState zeros out all fields in a ClientState
func clearState(state *ClientState) {
	log("Clearing ClientState fields")

	// Clear strings by overwriting each byte
	log("Clearing ID field (length: %d)", len(state.ID))
	state.ID = ""

	log("Clearing URL field (length: %d)", len(state.URL))
	state.URL = ""

	log("Clearing SessionAddr field (length: %d)", len(state.SessionAddr))
	state.SessionAddr = ""

	log("Clearing HMACKey field (length: %d)", len(state.HMACKey))
	state.HMACKey = ""

	log("Clearing Hostname field (length: %d)", len(state.Hostname))
	state.Hostname = ""

	log("Clearing OS field (length: %d)", len(state.OS))
	state.OS = ""

	log("Clearing ClientID field (length: %d)", len(state.ClientID))
	state.ClientID = ""

	// Clear numerics
	state.Jitter = 0
	state.Timer = 0
	log("Cleared numeric fields (Jitter, Timer)")

	// Clear metadata map
	if state.Metadata != nil {
		log("Clearing metadata map (size: %d)", len(state.Metadata))
		for k := range state.Metadata {
			delete(state.Metadata, k)
		}
		state.Metadata = nil
		log("Metadata map cleared")
	}

	log("All ClientState fields cleared")
}

// clearEncryptedState zeros out all fields in an EncryptedState
func clearEncryptedState(state *EncryptedState) {
	log("Clearing EncryptedState fields")

	if state.Ciphertext != nil {
		log("Clearing ciphertext (size: %d)", len(state.Ciphertext))
		for i := range state.Ciphertext {
			state.Ciphertext[i] = 0
		}
		state.Ciphertext = nil
		log("Ciphertext cleared")
	}

	if state.Nonce != nil {
		log("Clearing nonce (size: %d)", len(state.Nonce))
		for i := range state.Nonce {
			state.Nonce[i] = 0
		}
		state.Nonce = nil
		log("Nonce cleared")
	}

	if state.Salt != nil {
		log("Clearing salt (size: %d)", len(state.Salt))
		for i := range state.Salt {
			state.Salt[i] = 0
		}
		state.Salt = nil
		log("Salt cleared")
	}

	state.Timestamp = 0
	log("Timestamp cleared")
	log("All EncryptedState fields cleared")
}

// IsEncrypted returns whether the state is currently encrypted
func IsEncrypted() bool {
	log("Checking encryption state: %v", isEncrypted)
	return isEncrypted
}

// ClearMasterKey securely clears the master key from memory
func ClearMasterKey() {
	log("========== CLEARING MASTER KEY ==========")
	if masterKey != nil {
		log("Clearing master key (size: %d bytes)", len(masterKey))
		for i := range masterKey {
			masterKey[i] = 0
		}
		masterKey = nil
		log("Master key cleared and set to nil")

		// Force garbage collection
		log("Forcing garbage collection after key clear")
		runtime.GC()
		log("Garbage collection completed")
	} else {
		log("Master key is already nil, nothing to clear")
	}
	log("========== MASTER KEY CLEAR COMPLETE ==========")
}

// GetCurrentState returns the current decrypted state (if available)
func GetCurrentState() *ClientState {
	log("Getting current state (encrypted: %v, nil: %v)", isEncrypted, currentState == nil)
	return currentState
}

// CreateState creates a new ClientState from provided values
func CreateState(id, url, sessionAddr, hmacKey, hostname, os, clientID string, jitter, timer float64, metadata map[string]string) *ClientState {
	log("========== CREATING NEW CLIENT STATE ==========")
	log("ID: %s", id)
	log("URL: %s", url)
	log("SessionAddr: %s", sessionAddr)
	log("Hostname: %s", hostname)
	log("OS: %s", os)
	log("ClientID: %s", clientID)
	log("Jitter: %f", jitter)
	log("Timer: %f", timer)
	log("Metadata items: %d", len(metadata))

	state := &ClientState{
		ID:          id,
		Jitter:      jitter,
		Timer:       timer,
		URL:         url,
		SessionAddr: sessionAddr,
		HMACKey:     hmacKey,
		Hostname:    hostname,
		OS:          os,
		ClientID:    clientID,
		Metadata:    metadata,
	}

	currentState = state
	isEncrypted = false
	log("New client state created and set as current")
	log("========== STATE CREATION COMPLETE ==========")

	return state
}

// SetDebugMode allows external packages to enable/disable debug logging
func SetDebugMode(enabled bool) {
	debugMode = enabled
	log("Debug mode set to: %v", enabled)
}
