package main

import (
	"fmt"
	"net"
	"os"
	"runtime"
	"strings"
	"time"
)

type storageInfo struct {
	DriveName  string `json:"drive_name"`
	TotalSpace string `json:"total_space"`
	FreeSpace  string `json:"free_space"`
	UsedSpace  string `json:"used_space"`
}

type networkInterface struct {
	Name        string   `json:"name"`
	IPAddresses []string `json:"ip_addresses"`
	MACAddress  string   `json:"mac_address"`
}

type systemInfo struct {
	OsName            string             `json:"os_name"`
	OsVersion         string             `json:"os_version"`
	Architecture      string             `json:"architecture"`
	Hostname          string             `json:"hostname"`
	NetworkInterfaces []networkInterface `json:"network_interfaces"`
	CPU               string             `json:"cpu"`
	Memory            string             `json:"memory"`
	KernelVersion     string             `json:"kernel_version"`
	UpTime            string             `json:"uptime"`
	Storage           []storageInfo      `json:"storage"`
}

// --- Information Gathering Functions (Yaegi-compatible) ---

func getOSInfo() (string, string, string, string) {
	osName := runtime.GOOS
	arch := runtime.GOARCH
	osVersion := "Unknown"
	kernelVersion := "N/A"

	switch runtime.GOOS {
	case "linux":
		// Try to read /etc/os-release
		data, err := os.ReadFile("/etc/os-release")
		if err == nil {
			lines := strings.Split(string(data), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "PRETTY_NAME=") {
					osVersion = strings.Trim(strings.TrimPrefix(line, "PRETTY_NAME="), "\"")
					break
				}
			}
		}
		if osVersion == "Unknown" {
			osVersion = "Linux"
		}

		// Try to read kernel version from /proc/version
		data, err = os.ReadFile("/proc/version")
		if err == nil {
			parts := strings.Fields(string(data))
			if len(parts) >= 3 {
				kernelVersion = parts[2]
			}
		}

	case "darwin":
		osVersion = "macOS"
		kernelVersion = "Darwin"

	case "windows":
		osVersion = "Windows"
		kernelVersion = "N/A"

	default:
		osVersion = "Unknown"
		kernelVersion = "Unknown"
	}

	return osName, osVersion, arch, kernelVersion
}

func getHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		return "N/A"
	}
	return hostname
}

func getUptime() string {
	var uptime string

	switch runtime.GOOS {
	case "linux":
		data, err := os.ReadFile("/proc/uptime")
		if err == nil {
			fields := strings.Fields(string(data))
			if len(fields) > 0 {
				var seconds float64
				fmt.Sscanf(fields[0], "%f", &seconds)
				d := time.Duration(seconds) * time.Second
				days := int(d.Hours() / 24)
				hours := int(d.Hours()) % 24
				minutes := int(d.Minutes()) % 60
				uptime = fmt.Sprintf("%dd %dh %dm", days, hours, minutes)
			}
		}

	case "darwin":
		uptime = "N/A (requires sysctl)"

	case "windows":
		uptime = "N/A (requires systeminfo)"
	}

	if uptime == "" {
		uptime = "N/A"
	}
	return uptime
}

func getCPUInfo() string {
	var cpu string

	switch runtime.GOOS {
	case "linux":
		data, err := os.ReadFile("/proc/cpuinfo")
		if err == nil {
			lines := strings.Split(string(data), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "model name") {
					parts := strings.SplitN(line, ":", 2)
					if len(parts) == 2 {
						cpu = strings.TrimSpace(parts[1])
						break
					}
				}
			}
		}

	case "darwin":
		cpu = fmt.Sprintf("%s CPU", runtime.GOARCH)

	case "windows":
		cpu = fmt.Sprintf("%s CPU", runtime.GOARCH)
	}

	if cpu == "" {
		cpu = fmt.Sprintf("%s (%d cores)", runtime.GOARCH, runtime.NumCPU())
	}
	return cpu
}

func getMemoryInfo() string {
	var memory string

	switch runtime.GOOS {
	case "linux":
		data, err := os.ReadFile("/proc/meminfo")
		if err == nil {
			lines := strings.Split(string(data), "\n")
			var total, available, free uint64
			for _, line := range lines {
				fields := strings.Fields(line)
				if len(fields) < 2 {
					continue
				}
				var val uint64
				fmt.Sscanf(fields[1], "%d", &val)

				if strings.HasPrefix(line, "MemTotal:") {
					total = val * 1024 // Convert KB to bytes
				} else if strings.HasPrefix(line, "MemFree:") {
					free = val * 1024
				} else if strings.HasPrefix(line, "MemAvailable:") {
					available = val * 1024
				}
			}
			if total > 0 {
				totalGB := float64(total) / (1024 * 1024 * 1024)
				if available > 0 {
					availGB := float64(available) / (1024 * 1024 * 1024)
					usedPercent := float64(total-available) / float64(total) * 100
					memory = fmt.Sprintf("Total: %.2f GB, Available: %.2f GB, Used: %.1f%%",
						totalGB, availGB, usedPercent)
				} else {
					freeGB := float64(free) / (1024 * 1024 * 1024)
					usedPercent := float64(total-free) / float64(total) * 100
					memory = fmt.Sprintf("Total: %.2f GB, Free: %.2f GB, Used: %.1f%%",
						totalGB, freeGB, usedPercent)
				}
			}
		}

	case "darwin":
		memory = "N/A (requires vm_stat)"

	case "windows":
		memory = "N/A (requires systeminfo)"
	}

	if memory == "" {
		memory = "N/A"
	}
	return memory
}

func getNetworkInfo() []networkInterface {
	interfaces, err := net.Interfaces()
	if err != nil {
		return nil
	}

	var results []networkInterface
	for _, iface := range interfaces {
		// Skip loopback and down interfaces
		if iface.Flags&net.FlagLoopback != 0 || iface.Flags&net.FlagUp == 0 {
			continue
		}

		var ips []string
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}
			if ip != nil {
				ips = append(ips, ip.String())
			}
		}

		if len(ips) > 0 {
			results = append(results, networkInterface{
				Name:        iface.Name,
				IPAddresses: ips,
				MACAddress:  iface.HardwareAddr.String(),
			})
		}
	}
	return results
}

func getStorageInfo() []storageInfo {
	// Storage info requires external commands or system calls
	// Not easily accessible in Yaegi without os/exec
	return []storageInfo{
		{
			DriveName:  "N/A",
			TotalSpace: "N/A (requires df or wmic)",
			FreeSpace:  "N/A",
			UsedSpace:  "N/A",
		},
	}
}

func GetSystemInfo() systemInfo {
	osName, osVersion, arch, kernel := getOSInfo()

	info := systemInfo{
		OsName:            osName,
		OsVersion:         osVersion,
		Architecture:      arch,
		Hostname:          getHostname(),
		KernelVersion:     kernel,
		UpTime:            getUptime(),
		CPU:               getCPUInfo(),
		Memory:            getMemoryInfo(),
		NetworkInterfaces: getNetworkInfo(),
		Storage:           getStorageInfo(),
	}
	return info
}

func SysInfoString() string {
	info := GetSystemInfo()

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("OS:\t\t%s %s\n", info.OsName, info.OsVersion))
	sb.WriteString(fmt.Sprintf("Arch:\t\t%s\n", info.Architecture))
	sb.WriteString(fmt.Sprintf("Hostname:\t%s\n", info.Hostname))
	sb.WriteString(fmt.Sprintf("Kernel:\t\t%s\n", info.KernelVersion))
	sb.WriteString(fmt.Sprintf("Uptime:\t\t%s\n", info.UpTime))
	sb.WriteString(fmt.Sprintf("CPU:\t\t%s\n", info.CPU))
	sb.WriteString(fmt.Sprintf("Memory:\t\t%s\n", info.Memory))

	if len(info.Storage) > 0 {
		sb.WriteString("\nStorage:\n")
		for _, s := range info.Storage {
			sb.WriteString(fmt.Sprintf("  %s - Total: %s, Used: %s, Free: %s\n",
				s.DriveName, s.TotalSpace, s.UsedSpace, s.FreeSpace))
		}
	}

	if len(info.NetworkInterfaces) > 0 {
		sb.WriteString("\nNetwork Interfaces:\n")
		for _, ni := range info.NetworkInterfaces {
			sb.WriteString(fmt.Sprintf("  %s (%s):\n", ni.Name, ni.MACAddress))
			for _, ip := range ni.IPAddresses {
				sb.WriteString(fmt.Sprintf("    %s\n", ip))
			}
		}
	}

	return sb.String()
}

func Execute(args []string) (string, error) {
	return SysInfoString(), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
	return SysInfoString(), nil
}
