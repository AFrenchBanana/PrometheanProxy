#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <openssl/ssl.h>
#include <stdbool.h>
#include <arpa/inet.h>

#include "send_receive.h"

#define MAX_BUFFER_SIZE 4096

// Function to check if a file exists
bool check_file_exists(const char *file) {
    if (access(file, F_OK) != -1){
        return true;
    }
    return false;
}

void send_file(SSL* ssl) {
    char filename[256];
    strcpy(filename, receive_data(ssl));

    FILE *f = fopen(filename, "rb");
    if (f == NULL) {
        send_data(ssl, "Error");
        return;
    }

    fseek(f, 0, SEEK_END);
    long file_size = ftell(f);
    rewind(f);

    char *file_buffer = (char *)malloc(file_size);
    if (file_buffer == NULL) {
        send_data(ssl, "Error allocating memory");
        fclose(f);
        return;
    }

    size_t read_size = fread(file_buffer, 1, file_size, f);
    if (read_size != file_size) {
        send_data(ssl, "Error reading file");
        fclose(f);
        free(file_buffer);
        return;
    }
    fclose(f);

    // Send the file data
    uint32_t total_length = file_size;
    uint32_t chunk_size = MAX_BUFFER_SIZE;

    // Send the header
    if (send_header(ssl, total_length, chunk_size) < 0) {
        free(file_buffer);
        return;
    }

    // Send the data in chunks
    for (size_t i = 0; i < total_length; i += chunk_size) {
        size_t chunk_size_to_send = (i + chunk_size < total_length) ? chunk_size : total_length - i;
        const char* chunk = file_buffer + i;
        ssize_t sent_bytes = SSL_write(ssl, chunk, chunk_size_to_send);
        if (sent_bytes < 0 || sent_bytes != (ssize_t)chunk_size_to_send) {
            free(file_buffer);
            return;
        }
    }

    free(file_buffer);
}

void recv_file(SSL* ssl) {
    char filename[256];
    strcpy(filename, receive_data(ssl));
    if (strcmp(filename, "break") == 0)
        return;

    uint32_t total_length, chunk_size;
    // Receive total_length
    if (SSL_read(ssl, &total_length, sizeof(uint32_t)) <= 0) {
        return;
    }
    // Receive chunk_size
    if (SSL_read(ssl, &chunk_size, sizeof(uint32_t)) <= 0) {
        return;
    }
    // Convert from network to host byte order
    total_length = ntohl(total_length);
    chunk_size = ntohl(chunk_size);

    // Allocate memory for received_data
    char* received_data = (char*)malloc(total_length);
    if (received_data == NULL) {
        return;
    }

    size_t received_bytes = 0;
    while (received_bytes < total_length) {
        ssize_t bytes_received = SSL_read(ssl, received_data + received_bytes, total_length - received_bytes);
        // Check for errors
        if (bytes_received < 0) {
            free(received_data);
            return;
        }
        if (bytes_received == 0) {
            free(received_data);
            return;
        }
        received_bytes += bytes_received;
    }


    FILE *f = fopen(filename, "wb");
    if (f == NULL) {
        send_data(ssl, "Error: Cannot open file for writing");
        free(received_data);
        return;
    }
    // Write received data to file using the received file size
    fwrite(received_data, 1, received_bytes, f);
    fclose(f);
    free(received_data);

    bool exists = check_file_exists(filename);
    if (exists) {
        send_data(ssl, "True");
    } else {
        send_data(ssl, "False");
    }
}
