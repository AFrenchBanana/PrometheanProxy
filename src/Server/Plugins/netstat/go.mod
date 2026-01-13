module Plugins/systeminfo

go 1.24.3

require github.com/shirou/gopsutil/v3 v3.24.5

require (
	github.com/go-ole/go-ole v1.3.0 // indirect
	github.com/lufia/plan9stats v0.0.0-20250821153705-5981dea3221d // indirect
	github.com/power-devops/perfstat v0.0.0-20240221224432-82ca36839d55 // indirect
	github.com/shoenig/go-m1cpu v0.1.6 // indirect
	github.com/tklauser/go-sysconf v0.3.15 // indirect
	github.com/tklauser/numcpus v0.10.0 // indirect
	github.com/yusufpapurcu/wmi v1.2.4 // indirect
	golang.org/x/sys v0.35.0 // indirect
)

replace src/Client => ../../../Client/
