package config

type ObfuscationConfig struct {
	Generic struct {
		ImplantInfo ImplantInfo `json:"implant_info"`
		Commands    Commands    `json:"commands"`
	} `json:"generic"`
}

type ImplantInfo struct {
	Name    string `json:"Name"`
	OS      string `json:"os"`
	Address string `json:"address"`
	Timer   string `json:"timer"`
	Jitter  string `json:"jitter"`
	UUID    string `json:"uuid"`
}

type Commands struct {
	Name        string  `json:"obfuscation_name"`
	CommandUUID string  `json:"command_uuid"`
	Command     string  `json:"command"`
	Data        string  `json:"data"`
	Module      Module  `json:"module"`
	Shell       Command `json:"shell"`
	None        Command `json:"none"`
}

type Module struct {
	Name       string `json:"obfuscation_name"`
	ModuleName string `json:"module_name"`
	Data       string `json:"data"`
}

type Command struct {
	Name string `json:"obfuscation_name"`
}
