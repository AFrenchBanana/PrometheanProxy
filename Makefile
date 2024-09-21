CC = gcc
CFLAGS = -I/src/Client/Client_C/dep/openssl
LDFLAGS = -lssl -lcrypto
SOURCE_DIR = src/Client/Client_C/
OUTPUT_LINUX = client_linux.elf
OUTPUT_WINDOWS = client_windows.exe
WIN_CC = x86_64-w64-mingw32-gcc
WIN_CFLAGS = -I/usr/x86_64-w64-mingw32/include -L/usr/x86_64-w64-mingw32/lib -I/src/Client/Client_C/dep/openssl
WIN_LDFLAGS = -L/src/Client/Client_C/dep/openssl -lssl -lcrypto -lws2_32 -lbcrypt -lcrypt32 -liphlpapi -static

venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	echo "To activate the virtual environment, run: source venv/bin/activate"

lint:
	. venv/bin/activate && flake8 src/ && flake8 tests/

test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py
	
linux:
	$(CC) $(CFLAGS) -o $(OUTPUT_LINUX) $(SOURCE_DIR)main.c $(SOURCE_DIR)Linux/*.c $(SOURCE_DIR)Generic/*.c $(LDFLAGS)

windows:
	$(WIN_CC) $(WIN_CFLAGS) -o $(OUTPUT_WINDOWS) $(SOURCE_DIR)main.c $(SOURCE_DIR)Windows/*.c $(SOURCE_DIR)Generic/*.c $(WIN_LDFLAGS)

build: linux windows

rebuild: clean build

run: linux
	./$(OUTPUT_LINUX)

clean:
	rm -f $(OUTPUT_LINUX) $(OUTPUT_WINDOWS)
