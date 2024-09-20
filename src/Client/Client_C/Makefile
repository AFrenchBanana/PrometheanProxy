CC = gcc
CFLAGS =
LDFLAGS = -lssl -lcrypto
OUTPUT_LINUX = client_linux.elf
OUTPUT_WINDOWS = client_windows.exe
WIN_CC = x86_64-w64-mingw32-gcc
WIN_CFLAGS = -I/usr/x86_64-w64-mingw32/include -L/usr/x86_64-w64-mingw32/lib -I/home/ryan/openssl-mingw/openssl-1.1.1k/include
WIN_LDFLAGS = -L/home/ryan/openssl-mingw/openssl-1.1.1k/ -lssl -lcrypto -lws2_32 -lbcrypt -lcrypt32 -liphlpapi -static

linux:
	$(CC) $(CFLAGS) -o $(OUTPUT_LINUX) main.c Linux/*.c Generic/*.c $(LDFLAGS)

# Windows build
windows:
	$(WIN_CC) $(WIN_CFLAGS) -o $(OUTPUT_WINDOWS) main.c Windows/*.c Generic/*.c $(WIN_LDFLAGS)

# Build both
build: linux windows

# Rebuild both
rebuild: clean build

# Run Linux binary
run: build_linux
	./$(OUTPUT_LINUX)

# Clean both binaries
clean:
	rm -f $(OUTPUT_LINUX) $(OUTPUT_WINDOWS)
