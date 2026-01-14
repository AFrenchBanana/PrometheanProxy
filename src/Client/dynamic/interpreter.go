package dynamic

import (
	"fmt"
	"reflect"
	"src/Client/generic/commands"
	"src/Client/generic/logger"

	"github.com/traefik/yaegi/interp"
	"github.com/traefik/yaegi/stdlib"
	"github.com/traefik/yaegi/stdlib/unsafe"
)

type Interpreter struct {
	i                 *interp.Interpreter
	codeEvaluated     bool
	executeFunc       func([]string) (string, error)
	executeBeaconFunc func([]string, string) (string, error)
}

func NewInterpreter() *Interpreter {
	i := interp.New(interp.Options{
		GoPath: "", // Use empty string to allow standard library access
	})
	i.Use(stdlib.Symbols)
	i.Use(unsafe.Symbols) // Enable unsafe package for os/exec support
	i.Use(map[string]map[string]reflect.Value{
		"main/logger": {
			"Log": reflect.ValueOf(logger.Log),
		},
		"commands/commands": {
			"RunShellCommand":     reflect.ValueOf(commands.RunShellCommand),
		},
	})
	return &Interpreter{i: i}
}

func (i *Interpreter) Execute(code string, args []string) (string, error) {
	// Only evaluate the code once and cache the function
	if !i.codeEvaluated {
		_, err := i.i.Eval(code)
		if err != nil {
			return "", fmt.Errorf("failed to evaluate code: %w", err)
		}

		v, err := i.i.Eval("main.Execute")
		if err != nil {
			return "", fmt.Errorf("failed to find Execute function: %w", err)
		}

		execute, ok := v.Interface().(func([]string) (string, error))
		if !ok {
			return "", fmt.Errorf("Execute function has wrong signature")
		}

		i.executeFunc = execute
		i.codeEvaluated = true
		logger.Log("Code evaluated and Execute function cached")
	}

	return i.executeFunc(args)
}

func (i *Interpreter) ExecuteFromBeacon(code string, args []string, data string) (string, error) {
	// Only evaluate the code once and cache the function
	if !i.codeEvaluated {
		_, err := i.i.Eval(code)
		if err != nil {
			return "", fmt.Errorf("failed to evaluate code: %w", err)
		}

		v, err := i.i.Eval("main.ExecuteFromBeacon")
		if err != nil {
			return "", fmt.Errorf("failed to find ExecuteFromBeacon function: %w", err)
		}

		execute, ok := v.Interface().(func([]string, string) (string, error))
		if !ok {
			return "", fmt.Errorf("ExecuteFromBeacon function has wrong signature")
		}

		i.executeBeaconFunc = execute
		i.codeEvaluated = true
		logger.Log("Code evaluated and ExecuteFromBeacon function cached")
	}

	return i.executeBeaconFunc(args, data)
}
