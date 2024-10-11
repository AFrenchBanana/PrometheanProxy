LDFLAGS = -lssl -lcrypto -lcpprest -ljsoncpp
SOURCE_DIR = src/Client/Client_C++/
OUTPUT_LINUX = client_linux.elf
OUTPUT_WINDOWS = client_windows.exe
WIN_CC = x86_64-w64-mingw32-g++
WIN_CFLAGS = -I/usr/x86_64-w64-mingw32/include -L/usr/x86_64-w64-mingw32/lib -I/src/Client/Client_C++/dep/openssl -I/usr/include/cpprest -I/usr/include/jsoncpp
WIN_LDFLAGS = -L/src/Client/Client_C++/dep/openssl -lssl -lcrypto -lcpprest -lws2_32 -lbcrypt -lcrypt32 -liphlpapi -static -ljsoncpp


venv:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

lint:
	. venv/bin/activate && flake8 src/ && flake8 tests/

test:
	. venv/bin/activate && PYTHONPATH=src/Server python3 -m unittest tests/*.py
    
linux:
	$(CC) $(CFLAGS) -o $(OUTPUT_LINUX) $(SOURCE_DIR)main.cpp

windows:
	$(WIN_CC) $(WIN_CFLAGS) -o $(OUTPUT_WINDOWS) $(SOURCE_DIR)main.cpp $(SOURCE_DIR)Windows/*.cpp $(SOURCE_DIR)Generic/*.cpp $(WIN_LDFLAGS)
