//go:build linux
// +build linux

package main

import (
	"bufio"
	"os"
	"strconv"
	"strings"
)

// getSELinuxContext returns the SELinux context from /proc/self/attr/current if available.
func getSELinuxContext() string {
	b, err := os.ReadFile("/proc/self/attr/current")
	if err == nil {
		return strings.TrimSpace(string(b))
	}
	// older kernels may expose /proc/self/attr/exec or /selinux/context
	if b, err := os.ReadFile("/proc/self/attr/exec"); err == nil {
		return strings.TrimSpace(string(b))
	}
	if b, err := os.ReadFile("/selinux/context"); err == nil {
		return strings.TrimSpace(string(b))
	}
	return ""
}

// getLinuxCapabilities reads effective capabilities from /proc/self/status and returns human names when possible.
func getLinuxCapabilities() []string {
	f, err := os.Open("/proc/self/status")
	if err != nil {
		return nil
	}
	defer f.Close()
	var capEffHex string
	s := bufio.NewScanner(f)
	for s.Scan() {
		line := s.Text()
		if strings.HasPrefix(line, "CapEff:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				capEffHex = fields[1]
			}
			break
		}
	}
	if capEffHex == "" {
		return nil
	}
	// CapEff is hex bitmask
	v, err := strconv.ParseUint(capEffHex, 16, 64)
	if err != nil {
		return nil
	}
	// Map known Linux capability names from bit positions 0..63
	names := []string{
		"CAP_CHOWN", "CAP_DAC_OVERRIDE", "CAP_DAC_READ_SEARCH", "CAP_FOWNER", "CAP_FSETID",
		"CAP_KILL", "CAP_SETGID", "CAP_SETUID", "CAP_SETPCAP", "CAP_LINUX_IMMUTABLE",
		"CAP_NET_BIND_SERVICE", "CAP_NET_BROADCAST", "CAP_NET_ADMIN", "CAP_NET_RAW", "CAP_IPC_LOCK",
		"CAP_IPC_OWNER", "CAP_SYS_MODULE", "CAP_SYS_RAWIO", "CAP_SYS_CHROOT", "CAP_SYS_PTRACE",
		"CAP_SYS_PACCT", "CAP_SYS_ADMIN", "CAP_SYS_BOOT", "CAP_SYS_NICE", "CAP_SYS_RESOURCE",
		"CAP_SYS_TIME", "CAP_SYS_TTY_CONFIG", "CAP_MKNOD", "CAP_LEASE", "CAP_AUDIT_WRITE",
		"CAP_AUDIT_CONTROL", "CAP_SETFCAP", "CAP_MAC_OVERRIDE", "CAP_MAC_ADMIN", "CAP_SYSLOG",
		"CAP_WAKE_ALARM", "CAP_BLOCK_SUSPEND", "CAP_AUDIT_READ", "CAP_PERFMON", "CAP_BPF",
		"CAP_CHECKPOINT_RESTORE",
	}
	out := []string{}
	for i, name := range names {
		if v&(1<<uint(i)) != 0 {
			out = append(out, name)
		}
	}
	return out
}
