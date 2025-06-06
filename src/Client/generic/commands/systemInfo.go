package commands

import (
	"fmt"
	"net"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"

	"src/Client/generic/logger"
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

// bytesToGB converts bytes to a human-readable string in GB.
func bytesToGB(b uint64) string {
	return fmt.Sprintf("%.2f GB", float64(b)/float64(1<<30))
}

// --- Information Gathering Functions ---

func getOSInfo() (string, string, string, string) {
	logger.Log("Gathering OS information...")
	hostInfo, err := host.Info()
	logger.Log("OS information gathered.")
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get host info: %v", err))
		return runtime.GOOS, "N/A", runtime.GOARCH, "N/A"
	}
	logger.Log(fmt.Sprintf("OS: %s, Version: %s, Arch: %s, Kernel: %s",
		hostInfo.Platform, hostInfo.PlatformVersion, hostInfo.KernelArch, hostInfo.KernelVersion))
	return hostInfo.Platform, hostInfo.PlatformVersion, hostInfo.KernelArch, hostInfo.KernelVersion
}

func getHostname() string {
	logger.Log("Gathering hostname...")
	hostname, err := os.Hostname()
	logger.Log("Hostname gathered.")
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get hostname: %v", err))
		return "N/A"
	}
	logger.Log(fmt.Sprintf("Hostname: %s", hostname))
	return hostname
}

func getUptime() string {
	logger.Log("Gathering system uptime...")
	uptime, err := host.Uptime()
	logger.Log("Uptime gathered.")
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get uptime: %v", err))
		return "N/A"
	}
	d := time.Duration(uptime) * time.Second
	logger.Log(fmt.Sprintf("Uptime: %s", d.String()))
	return d.String()
}

func getCPUInfo() string {
	logger.Log("Gathering CPU information...")
	cpuInfos, err := cpu.Info()
	if err != nil || len(cpuInfos) == 0 {
		logger.Warn(fmt.Sprintf("Could not get CPU info: %v", err))
		return "N/A"
	}
	logger.Log(fmt.Sprintf("CPU Model: %s, Cores: %d, Frequency: %.2f MHz",
		cpuInfos[0].ModelName, cpuInfos[0].Cores, cpuInfos[0].Mhz))
	return cpuInfos[0].ModelName
}

func getMemoryInfo() string {
	logger.Log("Gathering memory information...")
	vmStat, err := mem.VirtualMemory()
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get memory info: %v", err))
		return "N/A"
	}
	logger.Log(fmt.Sprintf("Total Memory: %s, Free Memory: %s, Used Percent: %.2f%%",
		bytesToGB(vmStat.Total), bytesToGB(vmStat.Free), vmStat.UsedPercent))
	return fmt.Sprintf("Total: %s, Free: %s, Used: %.2f%%",
		bytesToGB(vmStat.Total), bytesToGB(vmStat.Free), vmStat.UsedPercent)
}

func getNetworkInfo() []networkInterface {
	logger.Log("Gathering network interface information...")
	interfaces, err := net.Interfaces()
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get network interfaces: %v", err))
		return nil
	}

	var results []networkInterface
	for _, iface := range interfaces {
		logger.Log(fmt.Sprintf("Processing interface: %s", iface.Name))
		// Ignore loopback and inactive interfaces
		if iface.Flags&net.FlagLoopback != 0 || iface.Flags&net.FlagUp == 0 {
			continue
		}

		var ips []string
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			// Extract IP address from CIDR notation
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
		logger.Log(fmt.Sprintf("Interface %s has IPs: %v", iface.Name, ips))

		if len(ips) > 0 {
			results = append(results, networkInterface{
				Name:        iface.Name,
				IPAddresses: ips,
				MACAddress:  iface.HardwareAddr.String(),
			})
		}
	}
	logger.Log(fmt.Sprintf("Found %d active network interfaces.", len(results)))
	return results
}

func getStorageInfo() []storageInfo {
	logger.Log("Gathering storage information...")
	partitions, err := disk.Partitions(true) // true for all partitions
	if err != nil {
		logger.Warn(fmt.Sprintf("Could not get disk partitions: %v", err))
		return nil
	}

	var results []storageInfo
	for _, p := range partitions {
		usage, err := disk.Usage(p.Mountpoint)
		if err != nil {
			continue
		}
		// Only include physical devices and common filesystems
		if strings.HasPrefix(p.Device, "/dev/loop") || usage.Total == 0 {
			continue
		}
		results = append(results, storageInfo{
			DriveName:  p.Mountpoint,
			TotalSpace: bytesToGB(usage.Total),
			FreeSpace:  bytesToGB(usage.Free),
			UsedSpace:  bytesToGB(usage.Used),
		})
	}
	logger.Log(fmt.Sprintf("Found %d storage devices.", len(results)))
	return results
}

func GetSystemInfo() systemInfo {
	logger.Log("Gathering complete system information...")
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
	logger.Log("System information gathered successfully.")
	return info
}

func SysInfoString() string {
	logger.Log("Generating system information string...")
	info := GetSystemInfo()
	return fmt.Sprintf(
		"OS:\t\t%s %s\n"+
			"Arch:\t\t%s\n"+
			"Hostname:\t%s\n"+
			"Kernel:\t\t%s\n"+
			"Uptime:\t\t%s\n"+
			"CPU:\t\t%s\n"+
			"Memory:\t\t%s\n"+
			"Storage:\n\t%v\n"+
			"Network Interfaces:\n\t%v",
		info.OsName,
		info.OsVersion,
		info.Architecture,
		info.Hostname,
		info.KernelVersion,
		info.UpTime,
		info.CPU,
		info.Memory,
		info.Storage,
		info.NetworkInterfaces,
	)
}
