//go:build !windows
// +build !windows

package main

// enrichWindowsPrivileges is a no-op on non-Windows platforms.
func enrichWindowsPrivileges(info *whoamiInfo) { /* no-op */ }
