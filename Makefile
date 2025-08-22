HMAC_KEY ?= $(shell cat $(HOME)/.PrometheanProxy/Certificates/hmac.key)

# Source and Output Directories
CLIENT_SOURCE_DIR = src/Client
SERVER_SOURCE_DIR = src/Server
OUTPUT_DIR = bin

# Define Go build flags
GO_BUILD_FLAGS = -ldflags="-s -w -X src/Client/generic/config.HMACKey=$(HMAC_KEY)"
GO_BUILD_FLAGS_DEBUG = -tags=debug -ldflags="-X src/Client/generic/config.HMACKey=$(HMAC_KEY)"

# Define output targets
OUTPUT_LINUX_RELEASE = $(OUTPUT_DIR)/promethean-client-linux-amd64
OUTPUT_LINUX_DEBUG = $(OUTPUT_DIR)/promethean-client-linux-amd64-debug
OUTPUT_WINDOWS_RELEASE = $(OUTPUT_DIR)/promethean-client-windows-amd64.exe
OUTPUT_WINDOWS_DEBUG = $(OUTPUT_DIR)/promethean-client-windows-amd64-debug.exe

# Discover Go plugins dynamically
PLUGIN_DIRS := $(filter-out template,$(notdir $(shell find plugins/* -maxdepth 0 -type d)))
PLUGIN_OUT_DIR_LINUX := $(OUTPUT_DIR)/plugins/linux/release
PLUGIN_OUT_DIR_WINDOWS := $(OUTPUT_DIR)/plugins/windows/release
PLUGIN_OUT_DIR_LINUX_DEBUG := $(OUTPUT_DIR)/plugins/linux/debug
PLUGIN_OUT_DIR_WINDOWS_DEBUG := $(OUTPUT_DIR)/plugins/windows/debug

PLUGIN_PLUGINS_LINUX := $(addprefix $(PLUGIN_OUT_DIR_LINUX)/,$(addsuffix .so,$(PLUGIN_DIRS)))
PLUGIN_PLUGINS_WINDOWS := $(addprefix $(PLUGIN_OUT_DIR_WINDOWS)/,$(addsuffix .dll,$(PLUGIN_DIRS)))
PLUGIN_PLUGINS_LINUX_DEBUG := $(addprefix $(PLUGIN_OUT_DIR_LINUX_DEBUG)/,$(addsuffix -debug.so,$(PLUGIN_DIRS)))
PLUGIN_PLUGINS_WINDOWS_DEBUG := $(addprefix $(PLUGIN_OUT_DIR_WINDOWS_DEBUG)/,$(addsuffix -debug.dll,$(PLUGIN_DIRS)))

.PHONY: all venv lint test clean server server-elf server-windows build linux windows run-client check-hmac-key plugins

all: build server

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint: venv
	. venv/bin/activate && flake8 $(SERVER_SOURCE_DIR) && flake8 tests/

test: venv
	. venv/bin/activate && PYTHONPATH=$(SERVER_SOURCE_DIR) python3 -m unittest tests/*.py

clean:
	rm -rf bin build dist *.egg-info PrometheanProxy.spec

server: venv
	@echo "--> Building Python server ELF with PyInstaller (Linux)..."
	. venv/bin/activate && pyinstaller \
	--onefile \
	--name PrometheanProxy \
	--distpath $(OUTPUT_DIR) \
	--workpath build/pyinstaller_work \
	--specpath build \
	--clean -y \
	--paths src \
	--hidden-import=engineio.async_drivers.threading \
	src/Server/server.py

# Alias for clarity; produces an ELF on Linux via PyInstaller
server-elf: server

# Windows build of the Python server using py2exe. Run on Windows only.
server-windows: venv
	@echo "--> Building Python server .exe with py2exe (Windows-only)..."
	@echo "    Note: py2exe only works on Windows. Run this target on a Windows host."
	. venv/bin/activate && pip install -q --upgrade py2exe || true
	. venv/bin/activate && python src/Server/setup_py2exe.py py2exe
	@mkdir -p $(OUTPUT_DIR)
	@if [ -f "dist/PrometheanProxy.exe" ]; then \
		mv -f dist/PrometheanProxy.exe $(OUTPUT_DIR)/promethean-server-windows-amd64.exe; \
	fi



$(OUTPUT_LINUX_RELEASE): $(PLUGIN_SYSTEMINFO)
	@echo "--> Building Go client for Linux (Release)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o ../../$@  main.go 

$(OUTPUT_LINUX_DEBUG): $(PLUGIN_SYSTEMINFO)
	@echo "--> Building Go client for Linux (Debug)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o ../../$@ main.go 
	
$(OUTPUT_WINDOWS_RELEASE):
	@echo "--> Building Go client for Windows (Release)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o ../../$@ main.go 

$(OUTPUT_WINDOWS_DEBUG):
	@echo "--> Building Go client for Windows (Debug)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o ../../$@ main.go

# Include plugins in overall build
plugins: plugins-linux plugins-windows 

plugins-linux: $(PLUGIN_PLUGINS_LINUX) $(PLUGIN_PLUGINS_LINUX_DEBUG)
plugins-windows: $(PLUGIN_PLUGINS_WINDOWS) $(PLUGIN_PLUGINS_WINDOWS_DEBUG)

build: linux windows plugins

$(PLUGIN_OUT_DIR_LINUX)/%.so:
	@echo "--> Building Go plugin for $* (Linux)..."
	@mkdir -p $(CURDIR)/$(PLUGIN_OUT_DIR_LINUX)
	cd plugins/$*/ && \
		GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o $(CURDIR)/$(PLUGIN_OUT_DIR_LINUX)/$*.so main.go

$(PLUGIN_OUT_DIR_WINDOWS)/%.dll:
	@echo "--> Building Go plugin for $* (Windows)..."
	@mkdir -p $(CURDIR)/$(PLUGIN_OUT_DIR_WINDOWS)
	cd plugins/$*/ && \
		GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o $(CURDIR)/$(PLUGIN_OUT_DIR_WINDOWS)/$*.dll main.go

$(PLUGIN_OUT_DIR_LINUX_DEBUG)/%-debug.so:
	@echo "--> Building Go plugin for $* (Linux, Debug)..."
	@mkdir -p $(CURDIR)/$(PLUGIN_OUT_DIR_LINUX_DEBUG)
	cd plugins/$*/ && \
		GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o $(CURDIR)/$(PLUGIN_OUT_DIR_LINUX_DEBUG)/$*-debug.so main.go

$(PLUGIN_OUT_DIR_WINDOWS_DEBUG)/%-debug.dll:
	@echo "--> Building Go plugin for $* (Windows, Debug)..."
	@mkdir -p $(CURDIR)/$(PLUGIN_OUT_DIR_WINDOWS_DEBUG)
	cd plugins/$*/ && \
		GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o $(CURDIR)/$(PLUGIN_OUT_DIR_WINDOWS_DEBUG)/$*-debug.dll main.go


linux: $(OUTPUT_LINUX_RELEASE) $(OUTPUT_LINUX_DEBUG)
windows: $(OUTPUT_WINDOWS_RELEASE) $(OUTPUT_WINDOWS_DEBUG)

check-hmac-key:
	@if [ -z "$(HMAC_KEY)" ]; then \
		echo "!! Error: HMAC key content is empty. Please provide the key content."; \
		exit 1; \
	fi

hmac-key:
	@echo "HMAC Key: $(HMAC_KEY)"

run-client: check-hmac-key
	@echo "--> Running Go client in debug mode..."
	cd $(CLIENT_SOURCE_DIR) && go run -tags=debug main.go -conn=beacon -hmac-key="$(HMAC_KEY)"

