package main

import (
	"fmt"
	"os/user"
	"runtime"
	"sort"
	"strings"
)

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
	if runtime.GOOS != "windows" {
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
	return b.String()
}

func Execute(args []string) (string, error) {
	return whoamiString(), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
	return whoamiString(), nil
}
