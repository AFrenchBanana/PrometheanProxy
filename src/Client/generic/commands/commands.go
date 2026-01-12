package commands

// BuiltInCommand defines the interface for commands compiled into the client binary.
// Registration happens via rpc_client.RegisterBuiltInCommand().
type BuiltInCommand interface {
	Execute(args []string) (string, error)
	ExecuteFromSession(args []string) (string, error)
	ExecuteFromBeacon(args []string, data string) (string, error)
}
