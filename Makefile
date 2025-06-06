# Variables
CLIENT_SOURCE_DIR = src/Client/
OUTPUT_DIR = bin
OUTPUT_LINUX_RELEASE = $(OUTPUT_DIR)/Executable.elf
OUTPUT_LINUX_DEBUG = $(OUTPUT_DIR)/Executable-debug.elf
OUTPUT_WINDOWS_RELEASE = $(OUTPUT_DIR)/Executable.exe
OUTPUT_WINDOWS_DEBUG = $(OUTPUT_DIR)/Executable-debug.exe
BUILD_DIR = build
BUILD_DIR_WIN = build-windows
BUILD_DIR_LIN = build

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint:
	. venv/bin/activate && flake8 src/Server && flake8 tests/

test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py

server: venv
	. venv/bin/activate && pyinstaller \
	--onefile \
	--name PrometheanProxy \
	src/Server/server.py \
	--paths src \
	--hidden-import=engineio.async_drivers.threading \
	--hidden-import=engineio.async_drivers.asyncio \
	--hidden-import=socketio.async_drivers.threading \
	--hidden-import=socketio.async_drivers.asyncio \
	--distpath bin \
	--workpath bin/work \
	--clean -y && rm -rf bin/work && rm -rf PrometheanProxy.spec

build-linux-release: 
	cd $(CLIENT_SOURCE_DIR) && go build -o $(OUTPUT_LINUX_RELEASE) main.go

build-linux-debug: 
	cd $(CLIENT_SOURCE_DIR) && go build -o $(OUTPUT_LINUX_DEBUG) -tags=debug main.go

build-windows-release: 
	cd $(CLIENT_SOURCE_DIR) && go build -o $(OUTPUT_WINDOWS_RELEASE) main.go

build-windows-debug: 
	cd $(CLIENT_SOURCE_DIR) && go build -o $(OUTPUT_WINDOWS_DEBUG) -tags=debug main.go

linux: build-linux-release build-linux-debug

windows: build-windows-release build-windows-debug

build: linux windows

.PHONY : venv lint test server build-linux-release build-linux-debug build-windows-release build-windows-debug linux windows build
