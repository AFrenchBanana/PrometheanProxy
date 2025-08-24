//go:build windows
// +build windows

package main

import (
	"fmt"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

// getWindowsGroupNames enumerates token groups and returns display names.
func getWindowsGroupNames() []string {
	var token windows.Token
	if err := windows.OpenProcessToken(windows.CurrentProcess(), windows.TOKEN_QUERY, &token); err != nil {
		return nil
	}
	defer token.Close()

	var needed uint32
	// First call to get required size
	_ = windows.GetTokenInformation(token, windows.TokenGroups, nil, 0, &needed)
	if needed == 0 {
		return nil
	}
	buf := make([]byte, needed)
	if err := windows.GetTokenInformation(token, windows.TokenGroups, &buf[0], uint32(len(buf)), &needed); err != nil {
		return nil
	}

	// TOKEN_GROUPS { uint32 GroupCount; SID_AND_ATTRIBUTES Groups[ANYSIZE_ARRAY]; }
	// Read GroupCount
	if len(buf) < int(unsafe.Sizeof(uint32(0))) {
		return nil
	}
	groupCount := *(*uint32)(unsafe.Pointer(&buf[0]))
	// Start of Groups array is right after the uint32 count (naturally aligned for SIDAndAttributes)
	base := uintptr(unsafe.Pointer(&buf[0])) + unsafe.Sizeof(uint32(0))
	step := unsafe.Sizeof(windows.SIDAndAttributes{})

	out := make([]string, 0, groupCount)
	for i := uint32(0); i < groupCount; i++ {
		saa := (*windows.SIDAndAttributes)(unsafe.Pointer(base + uintptr(i)*step))
		if saa == nil || saa.Sid == nil {
			continue
		}
		// Resolve SID to name/domain
		var use uint32
		var nameLen, domainLen uint32
		_ = windows.LookupAccountSid(nil, saa.Sid, nil, &nameLen, nil, &domainLen, &use)
		var display string
		if nameLen > 0 || domainLen > 0 {
			nameBuf := make([]uint16, nameLen)
			domainBuf := make([]uint16, domainLen)
			if err := windows.LookupAccountSid(nil, saa.Sid, &nameBuf[0], &nameLen, &domainBuf[0], &domainLen, &use); err == nil {
				name := windows.UTF16ToString(nameBuf)
				domain := windows.UTF16ToString(domainBuf)
				if domain != "" {
					display = domain + "\\" + name
				} else {
					display = name
				}
			}
		}
		if display == "" {
			display = saa.Sid.String()
		}
		attrs := decodeSidAttributes(saa.Attributes)
		if attrs != "" {
			out = append(out, fmt.Sprintf("%s (%s)", display, attrs))
		} else {
			out = append(out, display)
		}
	}
	return out
}

// getWindowsPrivilegesSummary enumerates token privileges and returns a compact description.
func getWindowsPrivilegesSummary() string {
	var token windows.Token
	if err := windows.OpenProcessToken(windows.CurrentProcess(), windows.TOKEN_QUERY, &token); err != nil {
		return ""
	}
	defer token.Close()

	var needed uint32
	_ = windows.GetTokenInformation(token, windows.TokenPrivileges, nil, 0, &needed)
	if needed == 0 {
		return ""
	}
	buf := make([]byte, needed)
	if err := windows.GetTokenInformation(token, windows.TokenPrivileges, &buf[0], uint32(len(buf)), &needed); err != nil {
		return ""
	}

	// TOKEN_PRIVILEGES { uint32 PrivilegeCount; LUID_AND_ATTRIBUTES Privileges[ANYSIZE_ARRAY]; }
	if len(buf) < int(unsafe.Sizeof(uint32(0))) {
		return ""
	}
	count := *(*uint32)(unsafe.Pointer(&buf[0]))
	base := uintptr(unsafe.Pointer(&buf[0])) + unsafe.Sizeof(uint32(0))
	step := unsafe.Sizeof(windows.LUIDAndAttributes{})

	lines := make([]string, 0, count)
	for i := uint32(0); i < count; i++ {
		la := (*windows.LUIDAndAttributes)(unsafe.Pointer(base + uintptr(i)*step))
		if la == nil {
			continue
		}
		// Privilege name resolution is optional; we present LUID if name API is unavailable
		name := fmt.Sprintf("LUID(%d:%d)", la.Luid.HighPart, la.Luid.LowPart)
		state := decodePrivilegeAttributes(la.Attributes)
		if state == "" {
			lines = append(lines, name)
		} else {
			lines = append(lines, fmt.Sprintf("%s: %s", name, state))
		}
	}
	return strings.Join(lines, "\n")
}

func decodeSidAttributes(a uint32) string {
	// Common SID attribute flags
	const (
		SE_GROUP_MANDATORY          = 0x00000001
		SE_GROUP_ENABLED_BY_DEFAULT = 0x00000002
		SE_GROUP_ENABLED            = 0x00000004
		SE_GROUP_OWNER              = 0x00000008
		SE_GROUP_USE_FOR_DENY_ONLY  = 0x00000010
		SE_GROUP_INTEGRITY          = 0x00000020
		SE_GROUP_INTEGRITY_ENABLED  = 0x00000040
		SE_GROUP_RESOURCE           = 0x20000000
		SE_GROUP_LOGON_ID           = 0xC0000000
	)
	var parts []string
	if a&SE_GROUP_MANDATORY != 0 {
		parts = append(parts, "MANDATORY")
	}
	if a&SE_GROUP_ENABLED_BY_DEFAULT != 0 {
		parts = append(parts, "ENABLED_BY_DEFAULT")
	}
	if a&SE_GROUP_ENABLED != 0 {
		parts = append(parts, "ENABLED")
	}
	if a&SE_GROUP_OWNER != 0 {
		parts = append(parts, "OWNER")
	}
	if a&SE_GROUP_USE_FOR_DENY_ONLY != 0 {
		parts = append(parts, "DENY_ONLY")
	}
	if a&SE_GROUP_INTEGRITY != 0 {
		parts = append(parts, "INTEGRITY")
	}
	if a&SE_GROUP_INTEGRITY_ENABLED != 0 {
		parts = append(parts, "INTEGRITY_ENABLED")
	}
	if a&SE_GROUP_RESOURCE != 0 {
		parts = append(parts, "RESOURCE")
	}
	if a&SE_GROUP_LOGON_ID != 0 {
		parts = append(parts, "LOGON_ID")
	}
	return strings.Join(parts, ", ")
}

func decodePrivilegeAttributes(a uint32) string {
	const (
		SE_PRIVILEGE_ENABLED_BY_DEFAULT = 0x00000001
		SE_PRIVILEGE_ENABLED            = 0x00000002
		SE_PRIVILEGE_REMOVED            = 0x00000004
		SE_PRIVILEGE_USED_FOR_ACCESS    = 0x80000000
	)
	var parts []string
	if a&SE_PRIVILEGE_ENABLED_BY_DEFAULT != 0 {
		parts = append(parts, "default")
	}
	if a&SE_PRIVILEGE_ENABLED != 0 {
		parts = append(parts, "enabled")
	}
	if a&SE_PRIVILEGE_REMOVED != 0 {
		parts = append(parts, "removed")
	}
	if a&SE_PRIVILEGE_USED_FOR_ACCESS != 0 {
		parts = append(parts, "used-for-access")
	}
	return strings.Join(parts, ", ")
}
