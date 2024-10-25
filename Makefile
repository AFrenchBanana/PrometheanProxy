# Variables
LDFLAGS = -lssl -lcrypto -lcpprest -ljsoncpp
SOURCE_DIR = src/Client/Client_C++
OUTPUT_DIR = bin
OUTPUT_LINUX = $(OUTPUT_DIR)/client_linux.elf
OUTPUT_WINDOWS = $(OUTPUT_DIR)/client_windows.exe
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
	. venv/bin/activate && flake8 src/ && flake8 tests/

test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py

linux:
	mkdir -p $(BUILD_DIR_LIN) && mkdir -p $(OUTPUT_DIR) && cd $(BUILD_DIR_LIN) && \
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++ \
		-DCMAKE_PREFIX_PATH="$(LINUX_PREFIX)" \
		-DOUTPUT_BINARY=$(OUTPUT_LINUX) \
		../$(SOURCE_DIR) && make
	rm -rf $(BUILD_DIR_LIN)

windows:
	mkdir -p $(BUILD_DIR_WIN) && mkdir -p $(OUTPUT_DIR) && cd $(BUILD_DIR_WIN) && \
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$(WIN_CC) -DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_PREFIX_PATH="$(WINDOWS_PREFIX)" \
		-DOUTPUT_BINARY=$(OUTPUT_WINDOWS) \
		../$(SOURCE_DIR) && make
	rm -rf $(BUILD_DIR_WIN)

all: linux windows

clean:
	find . -name "CMakeFiles" -exec rm -rf {} +   # Clean up CMakeFiles
	find . -name "CMakeCache.txt" -exec rm -f {} +  # Clean up CMakeCache
	rm -rf $(BUILD_DIR) $(BUILD_DIR_WIN) $(BUILD_DIR_LIN) $(OUTPUT_DIR)
