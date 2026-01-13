# Plugin System Documentation

## Overview

PrometheanProxy uses an **interpreted plugin system** powered by [Yaegi](https://github.com/traefik/yaegi), a Go interpreter. All plugins are loaded and executed as Go source code at runtime, eliminating the need for pre-compiled binaries or RPC communication.

## Architecture

### How It Works

1. **Server-side**: The server reads Go source code from `src/Server/Plugins/<plugin_name>/main.go`
2. **Transmission**: The source code is sent to the client (beacon or session) via the command protocol
3. **Client-side**: The client loads the source code into a Yaegi interpreter instance
4. **Execution**: When the command is invoked, the interpreter executes the cached function

### Key Benefits

- **Cross-platform**: No need for platform-specific binaries (.dll/.so)
- **No compilation**: Plugins work immediately without building
- **Version independent**: No Go version compatibility issues
- **Lightweight**: Small payload size (source code vs compiled binary)
- **Debugging**: Easy to modify and test plugins

## Plugin Structure

Each plugin must follow this structure:

```
src/Server/Plugins/
└── plugin_name/
    ├── main.go          # Plugin implementation (required)
    ├── obfuscate.json   # Command name obfuscation (optional)
    ├── plugin_name.py   # Server-side handler (optional)
    └── go.mod           # Module definition (not used for interpretation)
```

## Writing a Plugin

### Basic Template

```go
package main

import (
    "fmt"
    // Only use standard library imports
)

// Execute is called when the plugin runs in session mode
func Execute(args []string) (string, error) {
    return "Hello from session mode!", nil
}

// ExecuteFromBeacon is called when the plugin runs in beacon mode
func ExecuteFromBeacon(args []string, data string) (string, error) {
    return "Hello from beacon mode!", nil
}
```

### Requirements

1. **Package must be `main`**
2. **Must implement at least one of:**
   - `Execute([]string) (string, error)` - For session mode
   - `ExecuteFromBeacon([]string, string) (string, error)` - For beacon mode
3. **Use only standard library** - External dependencies are not supported by Yaegi
4. **No global state** - Each execution should be stateless

### Supported Imports

Yaegi supports most of the Go standard library:

- `fmt`, `strings`, `time`, `os`, `net`, `io`, `encoding/*`
- `crypto/*`, `hash/*`
- `regexp`, `sort`, `math`, `bytes`
- And more...

See [Yaegi stdlib support](https://github.com/traefik/yaegi/tree/master/stdlib) for full list.

### Unsupported Features

- External dependencies (e.g., `github.com/...`)
- CGO-based packages
- Unsafe pointer operations
- Assembly code

## Examples

### Simple Plugin (whoami)

```go
package main

import (
    "fmt"
    "os/user"
    "runtime"
)

func Execute(args []string) (string, error) {
    cur, err := user.Current()
    if err != nil {
        return "", err
    }
    return fmt.Sprintf("User: %s\nPlatform: %s", cur.Username, runtime.GOOS), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
    return Execute(args)
}
```

### Using Shell Commands (system_info)

```go
package main

import (
    "fmt"
    "os/exec"
    "strings"
    "runtime"
)

func getCPUInfo() string {
    var cpu string
    
    switch runtime.GOOS {
    case "linux":
        output, _ := exec.Command("sh", "-c", 
            "cat /proc/cpuinfo | grep 'model name' | head -1").Output()
        cpu = string(output)
    case "windows":
        output, _ := exec.Command("cmd", "/c", 
            "wmic cpu get name").Output()
        cpu = string(output)
    case "darwin":
        output, _ := exec.Command("sysctl", "-n", 
            "machdep.cpu.brand_string").Output()
        cpu = string(output)
    }
    
    return strings.TrimSpace(cpu)
}

func Execute(args []string) (string, error) {
    return fmt.Sprintf("CPU: %s", getCPUInfo()), nil
}

func ExecuteFromBeacon(args []string, data string) (string, error) {
    return Execute(args)
}
```

## Loading and Executing Plugins

### From Server CLI

```bash
# List available modules
(beacon) > modules

# Load a module onto beacon
(beacon) > load whoami

# Execute the loaded module
(beacon) > whoami
```

### Programmatically (Python)

```python
# Queue module load command
beacon_obj.load_module_direct_beacon(beacon_uuid, "whoami")

# Module is automatically loaded when beacon checks in
# Then execute via normal command
beacon_obj.execute_command(beacon_uuid, "whoami")
```

## Debugging

### Check Module Loading

Enable debug mode to see detailed logging:

```bash
# Server side
python3 main.py --log-level DEBUG

# Client side  
go run -tags=debug main.go ...
```

### Common Issues

1. **"failed to evaluate code"**
   - Check for syntax errors in Go code
   - Ensure all imports are from stdlib
   - Verify function signatures match `Execute` or `ExecuteFromBeacon`

2. **"failed to find Execute function"**
   - Make sure function is exported (starts with capital letter)
   - Verify function signature exactly matches requirement
   - Check that package is `main`

3. **"import error: unable to find source"**
   - You're using an external dependency
   - Rewrite to use only stdlib
   - Use `os/exec` to call system commands as workaround

## Best Practices

1. **Error Handling**: Always return descriptive errors
2. **Cross-platform**: Use `runtime.GOOS` to handle platform differences
3. **Timeout**: Keep execution time reasonable (< 30s recommended)
4. **Output Format**: Return human-readable strings or JSON
5. **Testing**: Test on all target platforms before deployment

## Performance Considerations

- **First execution**: ~10-50ms overhead for code evaluation
- **Subsequent executions**: Near-native performance (cached functions)
- **Memory**: ~2-5MB per loaded module
- **Load time**: Depends on source code size (~1-2ms per KB)

## Migration from RPC Plugins

If you have existing plugins using hashicorp/go-plugin:

1. Remove all RPC-related imports
2. Remove plugin server/client setup code
3. Keep only the core logic in `Execute` functions
4. Replace external dependencies with stdlib equivalents
5. Test with Yaegi interpreter

## Contributing

When adding new plugins:

1. Use only stdlib dependencies
2. Implement both `Execute` and `ExecuteFromBeacon`
3. Add platform-specific handling with `runtime.GOOS`
4. Document plugin functionality in comments
5. Test on Linux and Windows

## Resources

- [Yaegi Documentation](https://github.com/traefik/yaegi)
- [Go Standard Library](https://pkg.go.dev/std)
- [Example Plugins](src/Server/Plugins/)