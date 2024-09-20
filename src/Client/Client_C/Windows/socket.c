#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#include <openssl/ssl.h>
#include <openssl/err.h>
#include "send_receive.h"
#include "../Generic/string_manipulation.h"
#include "../Generic/hashing.h"

#pragma comment(lib, "Ws2_32.lib")


int sockfd;
struct sockaddr_in server_addr;
SSL *ssl;



SSL* ssl_connection(int port, const char* sock_address) {
  // Initialize Winsock for Windows
  WSADATA wsaData;
  if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
    printf("Failed to initialize Winsock.\n");
    return NULL;
  }

  sockfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
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
    closesocket(sockfd);
    return NULL;
  }

  // Specify the server address and port
  memset(&server_addr, 0, sizeof(server_addr));
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(port);
  server_addr.sin_addr.s_addr = inet_addr(sock_address);

  // Connect to the server
  if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
    perror("Error connecting to the server");
    closesocket(sockfd);
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
    closesocket(sockfd);
    SSL_CTX_free(ctx);
    return NULL;
  }

  return ssl;
}




char* get_hostname(){
    char buffer[1024];
    buffer[1023] = '\0';
    gethostname(buffer, 1023);
    char *hostname = malloc(sizeof(char) * 1024);
    strcpy(hostname, buffer);
    return hostname;
}

void authentication(){
    char * intial_key = receive_data(ssl); // Receive the initial key from the server
    socklen_t len = sizeof(server_addr); // Get the length of the server address
    if (getsockname(sockfd, (struct sockaddr*)&server_addr, &len) == -1) { // Get the socket name
        perror("Error getting socket name"); // Print error for debugging
    } 
    printf("Port number %d\n", ntohs(server_addr.sin_port));
    char port_str[6]; // Assuming the port number will not exceed 5 digits
    sprintf(port_str, "%d", ntohs(server_addr.sin_port)); // Convert port number to string
    char *key = malloc(strlen(intial_key) + strlen(port_str) + 1); // Allocate memory for the concatenated string
    strcpy(key, intial_key); // Copy the initial key to the new string
    free(intial_key); // Free the memory for the initial key
    strcat(key, port_str); // Concatenate the port number string to the new string
    char* rev_key = reverseString(key); // Reverse the string
    char output[129]; // Allocate memory for the hash
    sha512(rev_key, output); // Hash the key
    send_data(ssl, output); // Send the hash to the server
}