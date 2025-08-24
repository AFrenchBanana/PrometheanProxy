//go:build windows
// +build windows

package main

func getSELinuxContext() string      { return "" }
func getLinuxCapabilities() []string { return nil }
