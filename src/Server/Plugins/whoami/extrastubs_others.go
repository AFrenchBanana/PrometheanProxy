//go:build !windows && !linux
// +build !windows,!linux

package main

func getWindowsGroupNames() []string      { return nil }
func getWindowsPrivilegesSummary() string { return "" }
func getSELinuxContext() string           { return "" }
func getLinuxCapabilities() []string      { return nil }
