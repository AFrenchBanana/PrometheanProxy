package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "download_file"
)

// DownloadFileCommand implements shared.Command for HTTP downloads.
type DownloadFileCommand struct{}

// Execute is called when the command is run in the default context.
func (c *DownloadFileCommand) Execute(args []string) (string, error) {
	Logger.Log("DownloadFileCommand.Execute called")
	if len(args) < 1 {
		return "", fmt.Errorf("usage: download_file <url> [dest_path]")
	}
	url := args[0]
	dest := ""
	if len(args) >= 2 {
		dest = args[1]
	} else {
		dest = filepath.Base(url)
	}
	resp, err := http.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	outFile, err := os.Create(dest)
	if err != nil {
		return "", err
	}
	defer outFile.Close()
	_, err = io.Copy(outFile, resp.Body)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("Downloaded %s to %s", url, dest), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *DownloadFileCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("DownloadFileCommand.ExecuteFromSession called")
	return c.Execute(args)
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *DownloadFileCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("DownloadFileCommand.ExecuteFromBeacon called with data: %s", data))
	return c.Execute(args)
}

// --- Main function for the plugin executable ---
func main() {
	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &DownloadFileCommand{}},
		},
	})
}
