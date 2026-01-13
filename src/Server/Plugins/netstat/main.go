package main

import (
	"bufio"
	"fmt"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
)

type connectionInfo struct {
	Proto         string `json:"proto"`
	LocalAddress  string `json:"local_address"`
	LocalPort     uint32 `json:"local_port"`
	RemoteAddress string `json:"remote_address"`
	RemotePort    uint32 `json:"remote_port"`
	State         string `json:"state"`
	PID           int32  `json:"pid"`
	ProcessName   string `json:"process"`
}

// --- Linux-specific parsing ---

func parseHexIP(hex string, isIPv6 bool) string {
	if isIPv6 {
		// IPv6 hex format: 128 bits in hex
		if len(hex) < 32 {
			return hex
		}
		// Convert from little-endian hex format
		ip := make([]byte, 16)
		for i := 0; i < 16; i += 4 {
			for j := 0; j < 4; j++ {
				pos := (i + (3 - j)) * 2
				if pos+2 <= len(hex) {
					val, _ := strconv.ParseUint(hex[pos:pos+2], 16, 8)
					ip[i+j] = byte(val)
				}
			}
		}
		return fmt.Sprintf("%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x",
			ip[0], ip[1], ip[2], ip[3], ip[4], ip[5], ip[6], ip[7],
			ip[8], ip[9], ip[10], ip[11], ip[12], ip[13], ip[14], ip[15])
	}

	// IPv4: 8 hex chars
	if len(hex) < 8 {
		return hex
	}
	// Little-endian format
	b1, _ := strconv.ParseUint(hex[6:8], 16, 8)
	b2, _ := strconv.ParseUint(hex[4:6], 16, 8)
	b3, _ := strconv.ParseUint(hex[2:4], 16, 8)
	b4, _ := strconv.ParseUint(hex[0:2], 16, 8)
	return fmt.Sprintf("%d.%d.%d.%d", b1, b2, b3, b4)
}

func parseHexPort(hex string) uint32 {
	port, _ := strconv.ParseUint(hex, 16, 32)
	return uint32(port)
}

func stateFromHex(hex string) string {
	state, _ := strconv.ParseInt(hex, 16, 32)
	states := map[int64]string{
		0x01: "ESTABLISHED",
		0x02: "SYN_SENT",
		0x03: "SYN_RECV",
		0x04: "FIN_WAIT1",
		0x05: "FIN_WAIT2",
		0x06: "TIME_WAIT",
		0x07: "CLOSE",
		0x08: "CLOSE_WAIT",
		0x09: "LAST_ACK",
		0x0A: "LISTEN",
		0x0B: "CLOSING",
	}
	if s, ok := states[state]; ok {
		return s
	}
	return fmt.Sprintf("UNKNOWN(%d)", state)
}

func resolveProcNameLinux(inode string) (int32, string) {
	// Walk /proc to find the process that owns this socket inode
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return 0, ""
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}

		// Check /proc/[pid]/fd/*
		fdPath := fmt.Sprintf("/proc/%d/fd", pid)
		fds, err := os.ReadDir(fdPath)
		if err != nil {
			continue
		}

		for _, fd := range fds {
			linkPath := fmt.Sprintf("%s/%s", fdPath, fd.Name())
			target, err := os.Readlink(linkPath)
			if err != nil {
				continue
			}

			// Socket inodes look like "socket:[12345]"
			expectedSocket := fmt.Sprintf("socket:[%s]", inode)
			if target == expectedSocket {
				// Found it! Get process name
				cmdlinePath := fmt.Sprintf("/proc/%d/cmdline", pid)
				data, err := os.ReadFile(cmdlinePath)
				if err == nil && len(data) > 0 {
					// cmdline is null-separated
					parts := strings.Split(string(data), "\x00")
					if len(parts) > 0 && parts[0] != "" {
						// Get just the basename
						cmdParts := strings.Split(parts[0], "/")
						return int32(pid), cmdParts[len(cmdParts)-1]
					}
				}

				// Fallback to comm
				commPath := fmt.Sprintf("/proc/%d/comm", pid)
				data, err = os.ReadFile(commPath)
				if err == nil {
					return int32(pid), strings.TrimSpace(string(data))
				}
				return int32(pid), ""
			}
		}
	}
	return 0, ""
}

func parseLinuxProcNet(path, proto string, isIPv6 bool) []connectionInfo {
	file, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer file.Close()

	var results []connectionInfo
	scanner := bufio.NewScanner(file)

	// Skip header
	scanner.Scan()

	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 10 {
			continue
		}

		// Parse local address
		localParts := strings.Split(fields[1], ":")
		if len(localParts) != 2 {
			continue
		}
		localAddr := parseHexIP(localParts[0], isIPv6)
		localPort := parseHexPort(localParts[1])

		// Parse remote address
		remoteParts := strings.Split(fields[2], ":")
		if len(remoteParts) != 2 {
			continue
		}
		remoteAddr := parseHexIP(remoteParts[0], isIPv6)
		remotePort := parseHexPort(remoteParts[1])

		// Parse state
		state := stateFromHex(fields[3])

		// Parse inode
		inode := fields[9]

		// Resolve process
		pid, procName := resolveProcNameLinux(inode)

		results = append(results, connectionInfo{
			Proto:         proto,
			LocalAddress:  localAddr,
			LocalPort:     localPort,
			RemoteAddress: remoteAddr,
			RemotePort:    remotePort,
			State:         state,
			PID:           pid,
			ProcessName:   procName,
		})
	}

	return results
}

func getAllConnectionsLinux() []connectionInfo {
	var all []connectionInfo
	all = append(all, parseLinuxProcNet("/proc/net/tcp", "tcp", false)...)
	all = append(all, parseLinuxProcNet("/proc/net/tcp6", "tcp6", true)...)
	all = append(all, parseLinuxProcNet("/proc/net/udp", "udp", false)...)
	all = append(all, parseLinuxProcNet("/proc/net/udp6", "udp6", true)...)

	// Sort for stable output
	sort.Slice(all, func(i, j int) bool {
		if all[i].Proto != all[j].Proto {
			return all[i].Proto < all[j].Proto
		}
		if all[i].State != all[j].State {
			return all[i].State < all[j].State
		}
		if all[i].LocalAddress != all[j].LocalAddress {
			return all[i].LocalAddress < all[j].LocalAddress
		}
		if all[i].LocalPort != all[j].LocalPort {
			return all[i].LocalPort < all[j].LocalPort
		}
		if all[i].RemoteAddress != all[j].RemoteAddress {
			return all[i].RemoteAddress < all[j].RemoteAddress
		}
		if all[i].RemotePort != all[j].RemotePort {
			return all[i].RemotePort < all[j].RemotePort
		}
		return all[i].PID < all[j].PID
	})
	return all
}

func getAllConnections() []connectionInfo {
	switch runtime.GOOS {
	case "linux":
		return getAllConnectionsLinux()
	default:
		return []connectionInfo{
			{
				Proto:        runtime.GOOS,
				LocalAddress: "N/A",
				State:        "Unsupported OS",
				ProcessName:  "netstat only supports Linux with standard library",
			},
		}
	}
}

// NetstatString returns a human-readable table of connections similar to `netstat -tunap`.
func NetstatString() string {
	conns := getAllConnections()
	header := fmt.Sprintf("%-5s %-22s %-22s %-12s %-7s %s", "Proto", "Local Address", "Remote Address", "State", "PID", "Process")
	lines := make([]string, 0, len(conns)+2)
	lines = append(lines, header)
	lines = append(lines, strings.Repeat("-", len(header)))
	for _, c := range conns {
		l := c.LocalAddress
		if c.LocalPort != 0 {
			l = fmt.Sprintf("%s:%d", l, c.LocalPort)
		}
		r := c.RemoteAddress
		if c.RemotePort != 0 {
			r = fmt.Sprintf("%s:%d", r, c.RemotePort)
		}
		pidStr := ""
		if c.PID > 0 {
			pidStr = fmt.Sprintf("%d", c.PID)
		}
		line := fmt.Sprintf("%-5s %-22s %-22s %-12s %-7s %s", c.Proto, l, r, c.State, pidStr, c.ProcessName)
		lines = append(lines, line)
	}
	return strings.Join(lines, "\n")
}

func Execute(args []string) (string, error) {
	return NetstatString(), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
	return NetstatString(), nil
}
