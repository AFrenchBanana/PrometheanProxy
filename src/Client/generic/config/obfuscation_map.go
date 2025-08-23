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
	Module string `json:"module"`
	Shell  string `json:"shell"`
}
