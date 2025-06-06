HMAC_KEY ?= $(shell cat $(HOME)/.PrometheanProxy/Certificates/hmac.key)

# Source and Output Directories
CLIENT_SOURCE_DIR = src/Client
SERVER_SOURCE_DIR = src/Server
OUTPUT_DIR = bin

# Define Go build flags
GO_BUILD_FLAGS = -ldflags="-s -w" # Strips debug info and symbols for smaller release builds
GO_BUILD_FLAGS_DEBUG = -tags=debug

# Define output targets
OUTPUT_LINUX_RELEASE = $(OUTPUT_DIR)/promethean-client-linux-amd64
OUTPUT_LINUX_DEBUG = $(OUTPUT_DIR)/promethean-client-linux-amd64-debug
OUTPUT_WINDOWS_RELEASE = $(OUTPUT_DIR)/promethean-client-windows-amd64.exe
OUTPUT_WINDOWS_DEBUG = $(OUTPUT_DIR)/promethean-client-windows-amd64-debug.exe

.PHONY: all venv lint test clean server build linux windows run-client check-hmac-key

all: build server

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint: venv
	. venv/bin/activate && flake8 $(SERVER_SOURCE_DIR) && flake8 tests/

test: venv
	. venv/bin/activate && PYTHONPATH=$(SERVER_SOURCE_DIR) python3 -m unittest tests/*.py

clean:
	rm -rf venv bin build src/Server/__pycache__ src/Client/__pycache__ *.egg-info PrometheanProxy.spec

server: venv
	@echo "--> Building Python server executable..."
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



$(OUTPUT_LINUX_RELEASE):
	@echo "--> Building Go client for Linux (Release)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o ../../$@ main.go -hmac-key="$(HMAC_KEY)"

$(OUTPUT_LINUX_DEBUG):
	@echo "--> Building Go client for Linux (Debug)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=linux GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o ../../$@ main.go -hmac-key="$(HMAC_KEY)"

# Rule for Windows builds.
$(OUTPUT_WINDOWS_RELEASE):
	@echo "--> Building Go client for Windows (Release)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS) -o ../../$@ main.go -hmac-key="$(HMAC_KEY)"

$(OUTPUT_WINDOWS_DEBUG):
	@echo "--> Building Go client for Windows (Debug)..."
	@mkdir -p $(OUTPUT_DIR)
	cd $(CLIENT_SOURCE_DIR) && GOOS=windows GOARCH=amd64 go build $(GO_BUILD_FLAGS_DEBUG) -o ../../$@ main.go -hmac-key="$(HMAC_KEY)"

linux: $(OUTPUT_LINUX_RELEASE) $(OUTPUT_LINUX_DEBUG)
windows: $(OUTPUT_WINDOWS_RELEASE) $(OUTPUT_WINDOWS_DEBUG)
build: linux windows


check-hmac-key:
	@if [ -z "$(HMAC_KEY)" ]; then \
		echo "!! Error: HMAC key content is empty. Please provide the key content."; \
		exit 1; \
	fi

# run-client now passes the key content directly.
run-client: check-hmac-key
	@echo "--> Running Go client in debug mode..."
	cd $(CLIENT_SOURCE_DIR) && go run -tags=debug main.go -conn=beacon -hmac-key="$(HMAC_KEY)"

