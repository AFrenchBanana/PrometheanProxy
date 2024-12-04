# Define variables
VCPKG_DIR := src/Client/Client_C++/dep/vcpkg
VCPKG_INCLUDE_DIR := $(VCPKG_DIR)/installed/$(TRIPLET)/include
VCPKG_LIB_DIR := $(VCPKG_DIR)/installed/$(TRIPLET)/lib
VCPKG_TOOLCHAIN_FILE := $(VCPKG_DIR)/scripts/buildsystems/vcpkg.cmake

SOURCE_DIR := src/
OUTPUT_LINUX := bin/linux_app
OUTPUT_WINDOWS := bin/windows_app

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
