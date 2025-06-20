package config

import (
	"flag"
	"runtime"
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

	ConfigMutex             sync.RWMutex
	PrimaryConnectionMethod string = "beacon"
	HMACKey                 string
)

func init() {
	primaryConnPtr := flag.String("conn", PrimaryConnectionMethod, "The primary connection method (e.g., session, beacon, websocket) [optional]")
	hmacKeyPtr := flag.String("hmac-key", HMACKey, "The HMAC key for authentication [optional]")

	flag.Parse()

	PrimaryConnectionMethod = *primaryConnPtr
	HMACKey = *hmacKeyPtr
}
