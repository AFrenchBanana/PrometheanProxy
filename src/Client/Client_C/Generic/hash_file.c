#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>  
#include <sys/stat.h>  
#include <openssl/ssl.h>

#include "hashing.h"
#ifdef _WIN64
  #include "../Windows/send_receive.h"
#else
  #include "../Linux/send_receive.h"
#endif

#define MAX_FILENAME_LENGTH 1024 // Define a reasonable maximum filename length

void hash_file(SSL* ssl, const char *file_path) {
  puts("Hashing File");    
  char error_msg[MAX_FILENAME_LENGTH + 256]; // Declare error_msg here
  FILE *fp = fopen(file_path, "rb");
  if (fp == NULL) {
    int errsv = errno;
    snprintf(error_msg, sizeof(error_msg), "Error opening file: %s (%s)", file_path, strerror(errsv));
    send_data(ssl, "Error");
    send_data(ssl, error_msg);
    return;
  }
  printf("1\n");
  // Obtain file size
  fseek(fp, 0, SEEK_END);
  long file_size = ftell(fp);
  fseek(fp, 0, SEEK_SET);
    printf("File size: %ld\n", file_size);
  // Allocate memory for file data
  unsigned char *file_data = malloc(file_size);
  if (file_data == NULL) {
    fprintf(stderr, "Error: Memory allocation failed for file data\n");
    send_data(ssl, "Error");
    send_data(ssl, "Memory allocation error");
    fclose(fp);
    return;
  }

  // Read file into memory
  if (fread(file_data, 1, file_size, fp) != file_size) {
    fprintf(stderr, "Error: Failed to read file %s\n", file_path);
    send_data(ssl, "Error");
    snprintf(error_msg, sizeof(error_msg), "Error reading file: %s", file_path);
    send_data(ssl, error_msg);
    fclose(fp);
    free(file_data);
    return;
  }

  fclose(fp);

  // Calculate SHA-256 hash
  unsigned char data[SHA256_DIGEST_LENGTH];
  sha256(file_data, data); // Remove unnecessary casts (refer to hashing.h)

  // Clean up allocated memory
  free(file_data);

  // Send the hash to the client
  send_data(ssl, (char *)data);  // Cast might still be needed depending on send_data implementation

  // Add the closing curly brace for the function
}
