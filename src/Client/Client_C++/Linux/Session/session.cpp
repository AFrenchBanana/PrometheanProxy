#include "session.hpp"
#include <iostream>
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <sys/socket.h>
#include <cstdint>
#include <vector>
#include <iomanip>
#include <sstream>
#include <openssl/sha.h>
#include <algorithm>
#include "../../Generic/logging.hpp"

Session::Session(const std::string &serverAddress, int port)
    : serverAddress(serverAddress), port(port), sock(-1), ctx(nullptr), ssl(nullptr) {}

bool Session::connectToServer() {
    logger.log("Connecting to server at " + serverAddress + ":" + std::to_string(port));
    initOpenSSL();
    const SSL_METHOD* method = TLS_client_method();
    if (!method) {
        logger.error("Failed to load TLS method");
        ERR_print_errors_fp(stderr);
        return false;
    }
    ctx = SSL_CTX_new(method);
    if (!ctx) {
        logger.error("Failed to create SSL context");
        ERR_print_errors_fp(stderr);
        return false;
    }
    if (!createSocket() || !connectSocket()) {
        cleanup();
        return false;
    }
    ssl = SSL_new(ctx);
    if (!ssl) {
        logger.error("Failed to create SSL structure");
        cleanup();
        return false;
    }
    SSL_set_fd(ssl, sock);
    if (SSL_connect(ssl) <= 0) {
        logger.error("SSL connection failed");
        ERR_print_errors_fp(stderr);
        cleanup();
        return false;
    }
    logger.log("SSL connection established " + std::to_string(SSL_get_fd(ssl)) + " " + SSL_get_cipher(ssl));
    return true;
}

void Session::disconnect() {
    if (ssl) {
        SSL_shutdown(ssl);
        SSL_free(ssl);
    }
    if (sock != -1) {
        close(sock);
    }
    if (ctx) {
        SSL_CTX_free(ctx);
    }
    ssl = nullptr;
    sock = -1;
    ctx = nullptr;
}

bool Session::sendData(const std::string &data) {
    uint32_t total_length = data.size();
    logger.log("Sending data of length: " + std::to_string(total_length));
    const uint32_t chunk_size = 4096;
    uint32_t header[2] = { htonl(total_length), htonl(chunk_size) };
    
    if (SSL_write(ssl, header, sizeof(header)) != sizeof(header)) {
        logger.error("Failed to send header");
        return false;
    }
    logger.log("Header sent successfully. Total length: " + std::to_string(total_length) + ", Chunk size: " + std::to_string(chunk_size));
    
    for (size_t i = 0; i < total_length; i += chunk_size) {
        size_t end_index = (i + chunk_size < total_length) ? i + chunk_size : total_length;
        std::string chunk = data.substr(i, end_index - i);
        logger.log("Sending chunk from index " + std::to_string(i) + " to " + std::to_string(end_index) + " (size: " + std::to_string(chunk.size()) + ")");
        logger.log("Chunk content: " + chunk);
        size_t sent = 0;
        while (sent < chunk.size()) {
            ssize_t n = SSL_write(ssl, chunk.data() + sent, chunk.size() - sent);
            if (n <= 0) {
                logger.error("Failed to send chunk starting at index " + std::to_string(i) + ". Sent " + std::to_string(sent) + " bytes before error.");
                return false;
            }
            sent += n;
            logger.log("Sent " + std::to_string(n) + " bytes, total sent for current chunk: " + std::to_string(sent) + "/" + std::to_string(chunk.size()));
        }
        logger.log("Chunk sent successfully from index " + std::to_string(i));
    }
    logger.log("Data sent successfully");
    return true;
}

std::string Session::receiveData() {
    uint32_t header[2];
    if (SSL_read(ssl, header, sizeof(header)) != sizeof(header)) {
        logger.error("Failed to receive header");
        return "";
    }
    uint32_t total_length = ntohl(header[0]);
    uint32_t chunk_size = ntohl(header[1]);
    logger.log("Received data length: " + std::to_string(total_length));
    logger.log("Received chunk size: " + std::to_string(chunk_size));
    std::string received_data;
    received_data.reserve(total_length);
    
    while (total_length > 0) {
        uint32_t bytes_to_receive = (total_length < chunk_size) ? total_length : chunk_size;
        std::vector<char> buffer(bytes_to_receive);
        int received = SSL_read(ssl, buffer.data(), bytes_to_receive);
        if (received <= 0) {
            logger.error("Failed to receive data chunk");
            break;
        }
        received_data.append(buffer.data(), received);
        total_length -= received;
    }
    logger.log("Received data: " + received_data);
    return received_data;
}

std::string Session::authentication(const std::string &authKey) {
    struct sockaddr_in local_addr;
    socklen_t addr_len = sizeof(local_addr);
    if (getsockname(sock, (struct sockaddr*)&local_addr, &addr_len) == -1) {
        logger.error("Failed to retrieve client-side port");
        return "";
    }
    uint16_t client_port = ntohs(local_addr.sin_port);
    std::string input = authKey + std::to_string(client_port);
    logger.log("Input for authentication: " + input);
    std::reverse(input.begin(), input.end());
    logger.log("Reversed input for authentication: " + input);
    
    unsigned char hash[SHA512_DIGEST_LENGTH];
    SHA512(reinterpret_cast<const unsigned char*>(input.c_str()), input.size(), hash);
    
    std::ostringstream oss;
    for (int i = 0; i < SHA512_DIGEST_LENGTH; ++i)
        oss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(hash[i]);
    
    logger.log("Hash calculated for authentication: " + oss.str());
    return oss.str();
}

void Session::initOpenSSL() {
    SSL_library_init();
    logger.log("OpenSSL library initialized");
    SSL_load_error_strings();
    logger.log("OpenSSL error strings loaded");
}

bool Session::createSocket() {
    logger.log("Creating socket");
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        logger.error("Socket creation failed");
        return false;
    }
    return true;
}

bool Session::connectSocket() {
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    if (inet_pton(AF_INET, serverAddress.c_str(), &server_addr.sin_addr) <= 0) {
        logger.error("Invalid address");
        close(sock);
        logger.warn("socket closed");
        return false;
    }
    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) != 0) {
        logger.error("Connection failed");
        perror("Connection failed");
        close(sock);
        logger.warn("socket closed");
        return false;
    }
    return true;
}

void Session::cleanup() {
    if (sock != -1) {
        close(sock);
        logger.warn("socket closed");
    }
    if (ctx) {
        SSL_CTX_free(ctx);
        logger.warn("ssl context closed");
    }
}
