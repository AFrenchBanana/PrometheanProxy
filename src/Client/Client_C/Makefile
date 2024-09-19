# Variables
CC = gcc
CFLAGS = 
LDFLAGS = -lssl -lcrypto
output = client.elf

build:
	$(CC) $(CFLAGS) -o $(output) main.c Linux/*.c Generic/*.c $(LDFLAGS)

rebuild: clean build

run: build
	./$(output)

clean:
	rm -f $(output)