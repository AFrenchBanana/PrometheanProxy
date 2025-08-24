# Read HMAC key if present; keep empty (no error) if file is missing
HMAC_KEY ?= $(shell test -f $(HOME)/.PrometheanProxy/Certificates/hmac.key && cat $(HOME)/.PrometheanProxy/Certificates/hmac.key || echo)

# Source and Output Directories
CLIENT_SOURCE_DIR = src/Client
SERVER_SOURCE_DIR = src/Server
OUTPUT_DIR = bin

# Default obfuscate config path (adjust if your workspace differs)
OBFUSCATE_CONFIG ?= $(CURDIR)/src/Server/obfuscate.json

# Define Go build flags
GO_BUILD_FLAGS = -ldflags="-s -w -X src/Client/generic/config.HMACKey=$(HMAC_KEY) -X 'src/Client/generic/config.ObfuscateConfigPath=$(OBFUSCATE_CONFIG)'"
GO_BUILD_FLAGS_DEBUG = -tags=debug -ldflags="-X src/Client/generic/config.HMACKey=$(HMAC_KEY) -X 'src/Client/generic/config.ObfuscateConfigPath=$(OBFUSCATE_CONFIG)'"

# Define output targets
OUTPUT_LINUX_RELEASE = $(OUTPUT_DIR)/promethean-client-linux-amd64
OUTPUT_LINUX_DEBUG = $(OUTPUT_DIR)/promethean-client-linux-amd64-debug
OUTPUT_WINDOWS_RELEASE = $(OUTPUT_DIR)/promethean-client-windows-amd64.exe
OUTPUT_WINDOWS_DEBUG = $(OUTPUT_DIR)/promethean-client-windows-amd64-debug.exe

# Discover Go plugins dynamically from the server plugin source
PLUGINS_SRC_DIR := $(SERVER_SOURCE_DIR)/Plugins
# Only include directories that contain a main.go (skip __pycache__, etc.) and exclude template
RAW_PLUGIN_DIRS := $(shell for d in $(PLUGINS_SRC_DIR)/*; do \
	if [ -d $$d ] && [ -f $$d/main.go ]; then basename $$d; fi; \
done)
PLUGIN_DIRS := $(filter-out template,$(RAW_PLUGIN_DIRS))

# Compiled plugin output directories (per-plugin layout under Server/Plugins/<name>)
# Linux:   src/Server/Plugins/<name>/{release,debug}/<name>[ -debug].so
# Windows: src/Server/Plugins/<name>/{release,debug}/<name>[ -debug].dll
PLUGINS_RELEASE_LINUX := $(foreach p,$(PLUGIN_DIRS),$(PLUGINS_SRC_DIR)/$(p)/release/$(p).so)
PLUGINS_RELEASE_WINDOWS := $(foreach p,$(PLUGIN_DIRS),$(PLUGINS_SRC_DIR)/$(p)/release/$(p).dll)
PLUGINS_DEBUG_LINUX := $(foreach p,$(PLUGIN_DIRS),$(PLUGINS_SRC_DIR)/$(p)/debug/$(p)-debug.so)
PLUGINS_DEBUG_WINDOWS := $(foreach p,$(PLUGIN_DIRS),$(PLUGINS_SRC_DIR)/$(p)/debug/$(p)-debug.dll)

# Staging directory for bundling ONLY Python plugin sources (no Go artifacts)
PY_PLUGIN_STAGING_DIR := build/py_plugins

.PHONY: all venv lint test clean server server-elf server-windows build linux windows run-client check-hmac-key plugins py-plugins install-plugins install-py-plugins install-all-plugins

all: build server

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint: venv
	. venv/bin/activate && flake8 $(SERVER_SOURCE_DIR) && flake8 tests/

test: venv
	. venv/bin/activate && PYTHONPATH=$(SERVER_SOURCE_DIR) python3 -m unittest tests/*.py

clean:
	rm -rf bin build dist *.egg-info PrometheanProxy.spec \
	$(SERVER_SOURCE_DIR)/Plugins/*/release \
	$(SERVER_SOURCE_DIR)/Plugins/*/debug

server: venv plugins py-plugins
	@echo "--> Building Python server ELF with PyInstaller (Linux)..."
	rm -f PrometheanProxy.spec build/PrometheanProxy.spec; \
	# Ensure plugin output directories exist so --add-data paths are valid even if empty
	for p in $(PLUGIN_DIRS); do \
		mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$$p/release; \
		mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$$p/debug; \
	done; \
	. venv/bin/activate && pyinstaller \
	--onefile \
	--name PrometheanProxy \
	--distpath $(OUTPUT_DIR) \
	--workpath build/pyinstaller_work \
	--specpath build \
	--clean -y \
	--paths src \
	--collect-submodules Server.Plugins \
	--hidden-import=Server.Plugins \
	--add-data $(CURDIR)/src/Server/config.toml:embedded/ \
	--add-data $(CURDIR)/src/Server/obfuscate.json:embedded/ \
	--add-data $(CURDIR)/$(PY_PLUGIN_STAGING_DIR):embedded/pyplugins \
	$(foreach p,$(PLUGIN_DIRS),--add-data $(CURDIR)/$(PLUGINS_SRC_DIR)/$(p)/release:embedded/plugins/$(p)/release) \
	$(foreach p,$(PLUGIN_DIRS),--add-data $(CURDIR)/$(PLUGINS_SRC_DIR)/$(p)/debug:embedded/plugins/$(p)/debug) \
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

plugins-linux: $(PLUGINS_RELEASE_LINUX) $(PLUGINS_DEBUG_LINUX)
plugins-windows: $(PLUGINS_RELEASE_WINDOWS) $(PLUGINS_DEBUG_WINDOWS)

build: linux windows plugins

# Stage only Python files from src/Server/Plugins into build/py_plugins, preserving package layout
py-plugins:
	@echo "--> Staging Python plugin sources..."
	@rm -rf $(PY_PLUGIN_STAGING_DIR)
	@mkdir -p $(PY_PLUGIN_STAGING_DIR)
	# Copy .py files and each plugin's obfuscate.json while preserving directory structure under a top-level 'Plugins' package
	@rsync -a --prune-empty-dirs \
		--include '*/' \
		--include '*.py' \
		--include 'obfuscate.json' \
		--exclude '*' \
		$(SERVER_SOURCE_DIR)/Plugins/ $(PY_PLUGIN_STAGING_DIR)/Plugins/

# Install Python plugin sources (including obfuscate.json) for source runs
install-py-plugins: py-plugins
	@echo "--> Installing Python plugin sources to $$HOME/.PrometheanProxy/plugins/Plugins ..."
	@dest="$$HOME/.PrometheanProxy/plugins/Plugins"; \
	mkdir -p "$$dest"; \
	rsync -a --prune-empty-dirs \
		--include '*/' \
		--include '*.py' \
		--include 'obfuscate.json' \
		--exclude '*' \
		$(SERVER_SOURCE_DIR)/Plugins/ "$$dest"/
	@echo "--> Python plugins installed under $$HOME/.PrometheanProxy/plugins/Plugins"

# Convenience target to install both compiled and Python plugins
install-all-plugins: install-plugins install-py-plugins

# Install compiled Go plugin artifacts into the user's plugins directory for source runs
install-plugins: plugins
	@echo "--> Installing compiled plugins to $$HOME/.PrometheanProxy/plugins ..."
	@dest="$$HOME/.PrometheanProxy/plugins"; \
	mkdir -p "$$dest"; \
	for p in $(PLUGIN_DIRS); do \
		for ch in release debug; do \
			src_dir="$(PLUGINS_SRC_DIR)/$$p/$$ch"; \
			out_dir="$$dest/$$p/$$ch"; \
			if [ -d "$$src_dir" ]; then \
				mkdir -p "$$out_dir"; \
				find "$$src_dir" -maxdepth 1 -type f \( -name '*.so' -o -name '*.dll' \) -exec cp -f {} "$$out_dir/" \; ; \
			fi; \
		done; \
	done; \
	echo "--> Plugins installed under $$dest"



define GO_PLUGIN_RULES
$(PLUGINS_SRC_DIR)/$(1)/release/$(1).so:
	@echo "--> Building Go plugin for $(1) (Linux, Release)..."
	@mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/release
	cd $(PLUGINS_SRC_DIR)/$(1)/ && \
		GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/release/$(1).so .

$(PLUGINS_SRC_DIR)/$(1)/release/$(1).dll:
	@echo "--> Building Go plugin for $(1) (Windows, Release)..."
	@mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/release
	cd $(PLUGINS_SRC_DIR)/$(1)/ && \
		GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/release/$(1).dll .

$(PLUGINS_SRC_DIR)/$(1)/debug/$(1)-debug.so:
	@echo "--> Building Go plugin for $(1) (Linux, Debug)..."
	@mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/debug
	cd $(PLUGINS_SRC_DIR)/$(1)/ && \
		GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/debug/$(1)-debug.so .

$(PLUGINS_SRC_DIR)/$(1)/debug/$(1)-debug.dll:
	@echo "--> Building Go plugin for $(1) (Windows, Debug)..."
	@mkdir -p $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/debug
	cd $(PLUGINS_SRC_DIR)/$(1)/ && \
		GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o $(CURDIR)/$(PLUGINS_SRC_DIR)/$(1)/debug/$(1)-debug.dll .
endef

$(foreach p,$(PLUGIN_DIRS),$(eval $(call GO_PLUGIN_RULES,$(p))))


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
	cd $(CLIENT_SOURCE_DIR) && go run -tags=debug main.go -conn=beacon -hmac-key="$(HMAC_KEY)" -obfuscate="$(OBFUSCATE_CONFIG)"

