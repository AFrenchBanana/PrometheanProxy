package config

import (
	"runtime"
	"sync"
)

var (
	ID           string = ""
	Jitter       int    = 5
	Timer        int    = 10
	URL          string = "http://localhost:8000"
	OsIdentifier string = runtime.GOOS + " " + runtime.GOARCH + func() string {
		if IsDebug() {
			return " (DEBUG)"
		} else {
			return ""
		}
	}()

	ConfigMutex sync.RWMutex
)
