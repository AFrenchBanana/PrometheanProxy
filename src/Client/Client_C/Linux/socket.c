#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include "send_receive.h"
#include "../Generic/string_manipulation.h"
#include "../Generic/hashing.h"

int sockfd;
struct sockaddr_in server_addr;
SSL *ssl;

// Define types for PORT and SOCK_ADDRESS
typedef int PORT;
typedef const char* SOCK_ADDRESS;

SSL* ssl_connection(PORT port, SOCK_ADDRESS address) {
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == -1) {
        perror("Error creating socket");
        return NULL;
    }

    // Initialize the SSL library
    SSL_library_init();
    SSL_load_error_strings();
    OpenSSL_add_all_algorithms();

    // Create an SSL context
    SSL_CTX *ctx = SSL_CTX_new(TLS_client_method());
    if (!ctx) {
        perror("Error creating SSL context");
        ERR_print_errors_fp(stderr);
        close(sockfd);
        return NULL;
    }

    // Specify the server address and port
    memset(&server_addr, 0, sizeof(server_addr)); // Zero out structure
    server_addr.sin_family = AF_INET; // IPv4 address family
    server_addr.sin_port = htons(port); // Server port
    if (inet_pton(AF_INET, address, &server_addr.sin_addr) <= 0) { // Convert address to binary
        perror("Invalid address or address not supported");
        SSL_CTX_free(ctx);
        close(sockfd);
        return NULL;
    }

    // Connect to the server
    if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("Error connecting to the server");
        SSL_CTX_free(ctx);
        close(sockfd);
        return NULL;
    }

    // Create an SSL connection
    ssl = SSL_new(ctx);
    SSL_set_fd(ssl, sockfd);

    // Perform the SSL handshake
    if (SSL_connect(ssl) != 1) {
        perror("Error during SSL handshake");
        ERR_print_errors_fp(stderr);
        SSL_free(ssl);
        close(sockfd);
        SSL_CTX_free(ctx);
        return NULL;
    }

    puts("Connected to server");
    return ssl;
}

char* get_hostname(){
    char buffer[1024];
    buffer[1023] = '\0';
    gethostname(buffer, 1023);
    char *hostname = malloc(sizeof(char) * 1024);
    if (hostname != NULL) {
        strcpy(hostname, buffer);
    }
    return hostname;
}

void authentication(){
    char *initial_key = receive_data(ssl); // Receive the initial key from the server
    socklen_t len = sizeof(server_addr); // Get the length of the server address
    if (getsockname(sockfd, (struct sockaddr*)&server_addr, &len) == -1) { // Get the socket name
        perror("Error getting socket name"); // Print error for debugging
        return;
    } 
    char port_str[6]; // Assuming the port number will not exceed 5 digits
    sprintf(port_str, "%d", ntohs(server_addr.sin_port)); // Convert port number to string
    char *key = malloc(strlen(initial_key) + strlen(port_str) + 1); // Allocate memory for the concatenated string
    if (key == NULL) {
        perror("Error allocating memory for key");
        free(initial_key);
        return;
    }
    strcpy(key, initial_key); // Copy the initial key to the new string
    free(initial_key); // Free the memory for the initial key
    strcat(key, port_str); // Concatenate the port number string to the new string
    char* rev_key = reverseString(key); // Reverse the string
    if (rev_key == NULL) {
        perror("Error reversing the key");
        free(key);
        return;
    }
    char output[129]; // Allocate memory for the hash
    sha512(rev_key, output); // Hash the key
    send_data(ssl, output); // Send the hash to the server
    free(key); // Free the concatenated key
    free(rev_key); // Free the reversed key
}
