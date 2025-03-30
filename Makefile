# Variables
LDFLAGS = -lssl -lcrypto -lcpprest -ljsoncpp
SOURCE_DIR = src/Client/Client_C++
OUTPUT_DIR = bin
OUTPUT_LINUX_RELEASE = $(OUTPUT_DIR)/Executable.elf
OUTPUT_LINUX_DEBUG = $(OUTPUT_DIR)/Executable-debug.elf
OUTPUT_WINDOWS_RELEASE = $(OUTPUT_DIR)/Executable.exe
OUTPUT_WINDOWS_DEBUG = $(OUTPUT_DIR)/Executable-debug.exe
BUILD_DIR = build
BUILD_DIR_WIN = build-windows
BUILD_DIR_LIN = build
WIN_CC = x86_64-w64-mingw32-g++

# CMake paths
VCPKG_PATH = $(SOURCE_DIR)/dep/vcpkg
LINUX_PREFIX = $(VCPKG_PATH)/installed/x64-linux
WINDOWS_PREFIX = $(VCPKG_PATH)/installed/x64-mingw-static

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint:
	. venv/bin/activate && flake8 src/Server && flake8 tests/

test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py

linux: linux-release linux-debug

linux-release: vcpkg-dep-linux
	mkdir -p $(BUILD_DIR_LIN) && mkdir -p $(OUTPUT_DIR) && cd $(BUILD_DIR_LIN) && \
	cmake -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_PREFIX_PATH="$(LINUX_PREFIX)" \
		../$(SOURCE_DIR) && make && mv MyExecutable ../$(OUTPUT_LINUX_RELEASE)
	rm -rf $(BUILD_DIR_LIN)

linux-debug: vcpkg-dep-linux
	mkdir -p $(BUILD_DIR_LIN) && mkdir -p $(OUTPUT_DIR) && cd $(BUILD_DIR_LIN) && \
	cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=g++ \
		-DCMAKE_PREFIX_PATH="$(LINUX_PREFIX)" \
		-DCMAKE_CXX_FLAGS="-DDEBUG" \
		../$(SOURCE_DIR) && make && mv MyExecutable ../$(OUTPUT_LINUX_DEBUG)
	rm -rf $(BUILD_DIR_LIN)

windows: windows-release windows-debug

windows-release: vcpkg-dep-windows
	mkdir -p build-windows && mkdir -p bin && cd build-windows && \
	cmake -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
		../$(SOURCE_DIR) && make && mv MyExecutable.exe ../$(OUTPUT_WINDOWS_RELEASE)
	rm -rf $(BUILD_DIR_WIN)

windows-debug: vcpkg-dep-windows
	mkdir -p build-windows && mkdir -p bin && cd build-windows && \
	cmake -DCMAKE_BUILD_TYPE=Debug \
		-DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_PREFIX_PATH="$(WINDOWS_PREFIX)" \
		-DCMAKE_CXX_FLAGS="-DDEBUG" \
		../$(SOURCE_DIR) && make && mv MyExecutable.exe ../$(OUTPUT_WINDOWS_DEBUG)
	rm -rf $(BUILD_DIR_WIN)

all: all-release all-debug

all-release: linux-release windows-release

all-debug: linux-debug windows-debug

clean:
	find . -name "CMakeFiles" -exec rm -rf {} +  
	find . -name "CMakeCache.txt" -exec rm -f {} +
	rm -rf $(BUILD_DIR) $(BUILD_DIR_WIN) $(BUILD_DIR_LIN) $(OUTPUT_DIR)
	rm -rf $(OUTPUT_LINUX_RELEASE) $(OUTPUT_LINUX_DEBUG) $(OUTPUT_WINDOWS_RELEASE) $(OUTPUT_WINDOWS_DEBUG)

vcpkg-dep: vcpkg-dep-windows vcpkg-dep-linux

vcpkg-dep-windows:
	cd $(VCPKG_PATH) && ./vcpkg install curl:x64-mingw-static jsoncpp:x64-mingw-static openssl:x64-mingw-static  

vcpkg-dep-linux:
	cd $(VCPKG_PATH) && ./vcpkg install curl:x64-linux jsoncpp:x64-linux


.PHONY: venv lint test linux linux-release linux-debug windows windows-release windows-debug all all-release all-debug clean vcpkg-dep vcpkg-dep-windows vcpkg-dep-linux