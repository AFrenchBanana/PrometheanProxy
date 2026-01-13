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

type procInfo struct {
	PID        int32   `json:"pid"`
	Name       string  `json:"name"`
	Exe        string  `json:"exe"`
	Username   string  `json:"username"`
	CPUPercent float64 `json:"cpu_percent"`
	MemRSS     uint64  `json:"mem_rss_bytes"`
	MemPercent float32 `json:"mem_percent"`
	CreateTime int64   `json:"create_time_unix_ms"`
}

// --- Linux-specific process parsing ---

func listProcessesLinux() ([]procInfo, error) {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil, err
	}

	var infos []procInfo
	var totalMem uint64

	// Get total memory for percentage calculation
	meminfo, err := os.ReadFile("/proc/meminfo")
	if err == nil {
		lines := strings.Split(string(meminfo), "\n")
		for _, line := range lines {
			if strings.HasPrefix(line, "MemTotal:") {
				fields := strings.Fields(line)
				if len(fields) >= 2 {
					val, _ := strconv.ParseUint(fields[1], 10, 64)
					totalMem = val * 1024 // Convert KB to bytes
					break
				}
			}
		}
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		pidStr := entry.Name()
		pid, err := strconv.Atoi(pidStr)
		if err != nil {
			continue
		}

		// Read process info
		procPath := fmt.Sprintf("/proc/%s", pidStr)

		// Get command name from /proc/[pid]/comm
		name := ""
		commData, err := os.ReadFile(fmt.Sprintf("%s/comm", procPath))
		if err == nil {
			name = strings.TrimSpace(string(commData))
		}

		// Get executable path from /proc/[pid]/exe
		exe := ""
		exePath, err := os.Readlink(fmt.Sprintf("%s/exe", procPath))
		if err == nil {
			exe = exePath
		}

		// Get username from /proc/[pid]/status (Uid field)
		username := ""
		statusData, err := os.ReadFile(fmt.Sprintf("%s/status", procPath))
		if err == nil {
			lines := strings.Split(string(statusData), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "Uid:") {
					fields := strings.Fields(line)
					if len(fields) >= 2 {
						uid := fields[1]
						username = getUsername(uid)
						break
					}
				}
			}
		}

		// Get memory info from /proc/[pid]/status
		var memRSS uint64
		if err == nil {
			lines := strings.Split(string(statusData), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "VmRSS:") {
					fields := strings.Fields(line)
					if len(fields) >= 2 {
						val, _ := strconv.ParseUint(fields[1], 10, 64)
						memRSS = val * 1024 // Convert KB to bytes
						break
					}
				}
			}
		}

		// Calculate memory percentage
		var memPercent float32
		if totalMem > 0 && memRSS > 0 {
			memPercent = float32(memRSS) / float32(totalMem) * 100
		}

		// Get process creation time from /proc/[pid]/stat
		var createTime int64
		statData, err := os.ReadFile(fmt.Sprintf("%s/stat", procPath))
		if err == nil {
			// Parse stat file - fields are space-separated, but comm can contain spaces and is in parentheses
			statStr := string(statData)
			// Find the last ')' to skip the comm field
			lastParen := strings.LastIndex(statStr, ")")
			if lastParen > 0 && lastParen < len(statStr)-1 {
				fields := strings.Fields(statStr[lastParen+1:])
				// Field 20 (index 19 in the remaining fields) is starttime in clock ticks
				if len(fields) >= 20 {
					ticks, _ := strconv.ParseInt(fields[19], 10, 64)
					// Convert to milliseconds (assuming 100 Hz clock)
					createTime = ticks * 10
				}
			}
		}

		// CPU percentage is harder to calculate accurately without sampling
		// We'll leave it as 0 for now (would need multiple samples)
		cpuPercent := 0.0

		infos = append(infos, procInfo{
			PID:        int32(pid),
			Name:       name,
			Exe:        exe,
			Username:   username,
			CPUPercent: cpuPercent,
			MemRSS:     memRSS,
			MemPercent: memPercent,
			CreateTime: createTime,
		})
	}

	// Sort by memory percent desc (since we can't calculate CPU accurately)
	sort.Slice(infos, func(i, j int) bool {
		return infos[i].MemPercent > infos[j].MemPercent
	})

	return infos, nil
}

func getUsername(uid string) string {
	// Try to read /etc/passwd to resolve UID to username
	file, err := os.Open("/etc/passwd")
	if err != nil {
		return uid
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Split(line, ":")
		if len(fields) >= 3 {
			if fields[2] == uid {
				return fields[0]
			}
		}
	}
	return uid
}

// --- Cross-platform wrapper ---

func listProcesses() ([]procInfo, error) {
	switch runtime.GOOS {
	case "linux":
		return listProcessesLinux()
	default:
		return []procInfo{
			{
				PID:  0,
				Name: fmt.Sprintf("Unsupported OS: %s", runtime.GOOS),
				Exe:  "Process listing only supports Linux with standard library",
			},
		}, nil
	}
}

func formatProcessesTable(infos []procInfo) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%-8s %-8s %-8s %-12s %-16s %s\n", "PID", "CPU%", "MEM%", "RSS(MB)", "USER", "NAME")
	fmt.Fprintf(&b, "%s\n", strings.Repeat("-", 80))
	for _, pi := range infos {
		rssMB := float64(pi.MemRSS) / (1024 * 1024)
		fmt.Fprintf(&b, "%-8d %-8.1f %-8.1f %-12.1f %-16s %s\n",
			pi.PID, pi.CPUPercent, pi.MemPercent, rssMB, pi.Username, pi.Name)
	}
	return b.String()
}

func Execute(args []string) (string, error) {
	infos, err := listProcesses()
	if err != nil {
		return "", err
	}
	return formatProcessesTable(infos), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
	infos, err := listProcesses()
	if err != nil {
		return "", err
	}
	return formatProcessesTable(infos), nil
}
