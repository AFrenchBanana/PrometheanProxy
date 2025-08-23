package config

import (
	"encoding/json"
	"flag"
	"os"
	"runtime"
	"strings"
	"sync"
)

var (
	ID                 string = ""
	Jitter             int    = 5
	Timer              int    = 10
	URLPort            string = "8000"
	SessionAddressPort string = "2000"
	URL                string = "http://localhost:" + URLPort
	SessionAddr        string = "localhost:" + SessionAddressPort
	OsIdentifier       string = runtime.GOOS + " " + runtime.GOARCH + func() string {
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
		return
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
}
