package commands


type BuiltInCommand interface {
	Execute(args []string) (string, error)

	ExecuteFromSession(args []string) (string, error)

	ExecuteFromBeacon(args []string, data string) (string, error)
}


// CommandList holds a collection of built-in commands, keyed by their command name.
type CommandList struct {
	commands map[string]BuiltInCommand
}

// NewCommandList creates and returns a new initialized CommandList.
func NewCommandList() *CommandList {
	return &CommandList{
		commands: make(map[string]BuiltInCommand),
	}
}

// AddCommand registers a new built-in command.
func (cl *CommandList) AddCommand(name string, cmd BuiltInCommand) {
	cl.commands[name] = cmd
}

// GetCommand retrieves a built-in command by name.
func (cl *CommandList) GetCommand(name string) (BuiltInCommand, bool) {
	cmd, ok := cl.commands[name]
	return cmd, ok
}
