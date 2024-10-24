<<<<<<< HEAD
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
=======
# Define variables
VCPKG_DIR := src/Client/Client_C++/dep/vcpkg
VCPKG_INCLUDE_DIR := $(VCPKG_DIR)/installed/$(TRIPLET)/include
VCPKG_LIB_DIR := $(VCPKG_DIR)/installed/$(TRIPLET)/lib
VCPKG_TOOLCHAIN_FILE := $(VCPKG_DIR)/scripts/buildsystems/vcpkg.cmake

SOURCE_DIR := src/
OUTPUT_LINUX := bin/linux_app
OUTPUT_WINDOWS := bin/windows_app
>>>>>>> d6c7eda (crying)

CC := g++
WIN_CC := x86_64-w64-mingw32-g++
CFLAGS := -std=c++17
LDFLAGS := -lcpprest -lssl -lcrypto -lboost_system -lboost_filesystem

# Targets
.PHONY: venv lint test linux windows vcpkg-setup clean

# Python Virtual Environment
venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

# Code Linting
lint:
	. venv/bin/activate && flake8 src/Server && flake8 tests/

# Testing
test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py

<<<<<<< HEAD
linux: vcpkg-dep-linux
	mkdir -p $(BUILD_DIR_LIN) && mkdir -p $(OUTPUT_DIR) && cd $(BUILD_DIR_LIN) && \
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++ \
		-DCMAKE_PREFIX_PATH="$(LINUX_PREFIX)" \
		../$(SOURCE_DIR) && make
	rm -rf $(BUILD_DIR_LIN)

windows: vcpkg-dep-windows
	mkdir -p build-windows && mkdir -p bin && cd build-windows && \
	cmake -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_PREFIX_PATH="$(WINDOWS_PREFIX)" \
		../$(SOURCE_DIR) && make
	rm -rf $(BUILD_DIR_WIN)

all: linux windows

clean:
	find . -name "CMakeFiles" -exec rm -rf {} +  
	find . -name "CMakeCache.txt" -exec rm -f {} +
	rm -rf $(BUILD_DIR) $(BUILD_DIR_WIN) $(BUILD_DIR_LIN) $(OUTPUT_DIR)

vcpkg-dep: vcpkg-dep-windows vcpkg-dep-linux

vcpkg-dep-windows:
	cd $(VCPKG_PATH) && ./vcpkg install curl:x64-mingw-static jsoncpp:x64-mingw-static 

vcpkg-dep-linux:
	cd $(VCPKG_PATH) && ./vcpkg install curl:x64-linux jsoncpp:x64-linux


.PHONY: venv lint test linux windows all clean vcpkg-dep vcpkg-dep-windows vcpkg-dep-linux
=======
# Vcpkg Setup
vcpkg-setup:
	@git submodule update --init --recursive
	cd $(VCPKG_DIR) && ./bootstrap-vcpkg.sh
	cd $(VCPKG_DIR) && ./vcpkg integrate install && ./vcpkg install jsoncpp cpprestsdk

# Linux Build
linux: TRIPLET := x64-linux
linux: vcpkg-setup
	$(CC) $(CFLAGS) -o $(OUTPUT_LINUX) $(SOURCE_DIR)main.cpp \
		-I$(VCPKG_INCLUDE_DIR)/cpprest -L$(VCPKG_LIB_DIR) $(LDFLAGS) \
		-DCMAKE_TOOLCHAIN_FILE=$(VCPKG_TOOLCHAIN_FILE) -D__linux__

# Windows Build
windows: TRIPLET := x64-windows
windows: vcpkg-setup
	$(WIN_CC) -o $(OUTPUT_WINDOWS) $(SOURCE_DIR)main.cpp \
		-I$(VCPKG_INCLUDE_DIR)/cpprest -L$(VCPKG_LIB_DIR) $(LDFLAGS) \
		-DCMAKE_TOOLCHAIN_FILE=$(VCPKG_TOOLCHAIN_FILE)

# Clean target
clean:
	@echo "Cleaning up..."
	rm -rf $(VCPKG_DIR)/installed bin/
	@echo "Clean complete."
>>>>>>> d6c7eda (crying)
