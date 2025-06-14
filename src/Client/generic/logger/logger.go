package logger

import (
	"fmt"
	"os"
	"src/Client/generic/config"
	"time"
)

// unexported logger instance
type simpleLogger struct{}

var instance = &simpleLogger{}

// unexported helper to get formatted timestamp
func getCurrentTimestamp() string {
	return time.Now().Format("2006-01-02 15:04:05")
}

// Log prints a standard log message if DEBUG is true.
func Log(msg string) {
	if config.IsDebug() {
		fmt.Printf("\033[32m[LOG] [%s] %s\033[0m\n", getCurrentTimestamp(), msg)
	}
}

func Warn(msg string) {
	if config.IsDebug() {
		fmt.Printf("\033[33m[WARN] [%s] %s\033[0m\n", getCurrentTimestamp(), msg)
	}
}

// Error prints an error message to stderr if DEBUG is true.
func Error(msg string) {
	if config.IsDebug() {
		fmt.Fprintf(os.Stderr, "\033[31m[ERROR] [%s] %s\033[0m\n", getCurrentTimestamp(), msg)
	}
}

func Fatal(msg string) {
	if config.IsDebug() {
		fmt.Fprintf(os.Stderr, "\033[31m[FATAL] [%s] %s\033[0m\n", getCurrentTimestamp(), msg)
	}
}
