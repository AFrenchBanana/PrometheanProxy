//go:build windows
// +build windows

package main

import (
	"fmt"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

// enrichWindowsPrivileges populates whoamiInfo.Privileged and Notes using Windows Token APIs.
func enrichWindowsPrivileges(info *whoamiInfo) {
	// Default heuristic note gets replaced with concrete findings.
	// Open the process token (self)
	var token windows.Token
	err := windows.OpenProcessToken(windows.CurrentProcess(), windows.TOKEN_QUERY, &token)
	if err != nil {
		info.Notes = append(info.Notes, fmt.Sprintf("OpenProcessToken failed: %v (falling back to heuristics)", err))
		heuristicWindowsPriv(info)
		return
	}
	defer token.Close()

	// 1) Check elevation state via TokenElevation (TokenIsElevated != 0 means elevated)
	var elevation uint32
	var retLen uint32
	err = windows.GetTokenInformation(token, windows.TokenElevation, (*byte)(unsafe.Pointer(&elevation)), uint32(unsafe.Sizeof(elevation)), &retLen)
	if err == nil {
		if elevation != 0 {
			info.Notes = append(info.Notes, "TokenElevation: Elevated")
			info.Privileged = true
		} else {
			info.Notes = append(info.Notes, "TokenElevation: Not elevated")
		}
	} else {
		info.Notes = append(info.Notes, fmt.Sprintf("GetTokenInformation(TokenElevation) failed: %v", err))
	}

	// 2) Check if user is member of the Administrators group
	// Build the SID for the builtin Administrators group
	var adminSID *windows.SID
	if err := windows.AllocateAndInitializeSid(&windows.SECURITY_NT_AUTHORITY, 2, windows.SECURITY_BUILTIN_DOMAIN_RID, windows.DOMAIN_ALIAS_RID_ADMINS, 0, 0, 0, 0, 0, 0, &adminSID); err == nil {
		defer windows.FreeSid(adminSID)
		// CheckTokenMembership via Token.IsMember
		isMember, err := token.IsMember(adminSID)
		if err == nil {
			if isMember {
				info.Notes = append(info.Notes, "Token is member of BUILTIN\\Administrators")
				info.Privileged = true
			} else {
				info.Notes = append(info.Notes, "Token is NOT member of BUILTIN\\Administrators")
			}
		} else {
			info.Notes = append(info.Notes, fmt.Sprintf("Token.IsMember(Admins) failed: %v", err))
		}
	} else {
		info.Notes = append(info.Notes, fmt.Sprintf("AllocateAndInitializeSid(Admins) failed: %v", err))
	}

	// 3) Heuristic fallback on username for SYSTEM/Administrator if nothing else marked privileged
	if !info.Privileged {
		heuristicWindowsPriv(info)
	}
}

func heuristicWindowsPriv(info *whoamiInfo) {
	uname := strings.ToLower(info.Username)
	if strings.HasSuffix(uname, "\\administrator") || strings.HasSuffix(uname, "\\system") || strings.Contains(uname, "administrator") {
		info.Privileged = true
	}
}
