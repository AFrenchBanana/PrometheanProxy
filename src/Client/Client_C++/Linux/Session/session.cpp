// #include "session.hpp"
// #include <iostream>
// #include <cstring>
// #include <chrono>
// #include <thread>
// #include <arpa/inet.h>
// #include <vector>
// #include <unistd.h>
// #include <openssl/ssl.h>
// #include <openssl/err.h>
// #include <algorithm>

// namespace {
//     const char* server_ip   = "127.0.0.1";
//     const int   server_port = 2000;
// }



// Session::Session() : ctx(nullptr), ssl(nullptr), sockfd(-1) {}

// Session::~Session() {
//     if (ssl)
//         SSL_free(ssl);
//     if (ctx)
//         SSL_CTX_free(ctx);
//     if (sockfd >= 0)
//         close(sockfd);
// }

// void Session::initSSL() {
//     SSL_load_error_strings();
//     OpenSSL_add_ssl_algorithms();
// }

// void Session::cleanupSSL() {
//     EVP_cleanup();
// }

// std::string Session::authentication(const std::string &auth_key) {
//     unsigned char hash[EVP_MAX_MD_SIZE];
//     unsigned int hash_len = 0;
//     EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
//     if (!mdctx) {
//         std::cerr << "[DEBUG] EVP_MD_CTX_new() failed" << std::endl;
//         return "";
//     }
//     if (EVP_DigestInit_ex(mdctx, EVP_sha512(), nullptr) != 1) {
//         std::cerr << "[DEBUG] EVP_DigestInit_ex() failed" << std::endl;
//         EVP_MD_CTX_free(mdctx);
//         return "";
//     }
//     if (EVP_DigestUpdate(mdctx, auth_key.c_str(), auth_key.size()) != 1) {
//         std::cerr << "[DEBUG] EVP_DigestUpdate() failed" << std::endl;
//         EVP_MD_CTX_free(mdctx);
//         return "";
//     }
//     if (EVP_DigestFinal_ex(mdctx, hash, &hash_len) != 1) {
//         std::cerr << "[DEBUG] EVP_DigestFinal_ex() failed" << std::endl;
//         EVP_MD_CTX_free(mdctx);
//         return "";
//     }
//     EVP_MD_CTX_free(mdctx);
    
//     std::ostringstream oss;
//     for (unsigned int i = 0; i < hash_len; i++) {
//         oss << std::hex << std::setw(2) << std::setfill('0') << (int)hash[i];
//     }
//     return oss.str();
// }

// bool Session::socketInitialization() {
//     // Use TLS_client_method() for a client context.
//     const SSL_METHOD* method = TLS_client_method();
//     ctx = SSL_CTX_new(method);
//     if (!ctx) {
//         std::cerr << "Unable to create SSL context\n";
//         return false;
//     }

//     // Disable certificate validation for demonstration (not secure in production).
//     SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, nullptr);

//     // Create a raw socket.
//     sockfd = ::socket(AF_INET, SOCK_STREAM, 0);
//     if (sockfd < 0) {
//         std::cerr << "Could not create socket\n";
//         return false;
//     }

//     // Create an SSL object and associate it with the socket.
//     ssl = SSL_new(ctx);
//     if (!ssl) {
//         std::cerr << "SSL_new() failed\n";
//         return false;
//     }
//     SSL_set_fd(ssl, sockfd);

//     return true;
// }

// bool Session::connection() {
//     sockaddr_in addr;
//     std::memset(&addr, 0, sizeof(addr));
//     addr.sin_family      = AF_INET;
//     addr.sin_port        = htons(server_port);
//     addr.sin_addr.s_addr = inet_addr(server_ip);

//     std::cout << "[DEBUG] Attempting to connect to " << server_ip << ":" << server_port << std::endl;

//     // Repeatedly try to connect every 5 seconds.
//     while (true) {
//         std::cout << "[DEBUG] Trying to connect socket " << sockfd << std::endl;
//         if (::connect(sockfd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) == 0) {
//             std::cout << "[DEBUG] Socket connection established. Initiating SSL handshake." << std::endl;
//             if (SSL_connect(ssl) <= 0) {
//                 std::cerr << "[DEBUG] SSL_connect() failed" << std::endl;
//                 return false;
//             }
//             std::cout << "[DEBUG] SSL handshake successful." << std::endl;

//             // Receive data from the server.
//             std::string received_data = receiveData();
//             if (received_data.empty()) {
//                 std::cerr << "[DEBUG] Failed to receive data." << std::endl;
//                 return false;
//             }

//             // Retrieve the local port.
//             sockaddr_in localAddr;
//             socklen_t addr_len = sizeof(localAddr);
//             if (getsockname(sockfd, reinterpret_cast<struct sockaddr*>(&localAddr), &addr_len) != 0) {
//                 std::cerr << "[DEBUG] getsockname() failed." << std::endl;
//                 return false;
//             }
//             int port = ntohs(localAddr.sin_port);

//             // Combine received data and port, then reverse the string.
//             std::string combined = received_data + std::to_string(port);
//             std::reverse(combined.begin(), combined.end());

//             // Calculate the SHA-512 hash using our authentication function.
//             std::string auth_hash = authentication(combined);

//             // Send the authentication hash back.
//             if (!sendData(auth_hash)) {
//                 std::cerr << "[DEBUG] Failed to send authentication hash." << std::endl;
//                 return false;
//             }
//             return true;
//         } else {
//             std::cerr << "[DEBUG] Connection attempt failed. Retrying in 5 seconds..." << std::endl;
//             std::this_thread::sleep_for(std::chrono::seconds(5));
//         }
//     }
//     return false; // Unreachable.
// }



// void Session::checkListener() {
//     std::string ans = receiveData();
//     if (ans == "true") {
//         std::string sharkport = receiveData();
//         listenerThread = std::thread([this, sharkport]() {
//             // Placeholder for additional background logic.
//             while (true) {
//                 // E.g., process periodic tasks
//                 std::this_thread::sleep_for(std::chrono::seconds(1));
//             }
//         });
//         listenerThread.detach();
//     }
// }

// bool Session::sendData(const std::string &data) {
//     int ret = SSL_write(ssl, data.c_str(), data.size());
//     return ret > 0;
// }

// bool Session::send_data(int sockfd, const std::string &data) {
//     uint32_t total_length = static_cast<uint32_t>(data.size());
//     uint32_t chunk_size   = 4096; 

//     // Pack header fields in network byte order.
//     uint32_t net_total_length = htonl(total_length);
//     uint32_t net_chunk_size   = htonl(chunk_size);

//     // Send the header.
//     if (send(sockfd, &net_total_length, sizeof(net_total_length), 0) < 0) {
//         return false;
//     }
//     if (send(sockfd, &net_chunk_size, sizeof(net_chunk_size), 0) < 0) {
//         return false;
//     }

//     // Send data in chunks.
//     size_t offset = 0;
//     while (offset < total_length) {
//         size_t to_send = std::min(static_cast<size_t>(chunk_size), total_length - offset);
//         ssize_t sent   = send(sockfd, data.data() + offset, to_send, 0);
//         if (sent <= 0) {
//             return false;
//         }
//         offset += sent;
//     }
//     return true;
// }

// bool Session::receive_data(int sockfd, std::string &data) {
//     uint32_t net_total_length, net_chunk_size;

//     // Receive the 8-byte header.
//     if (recv(sockfd, &net_total_length, sizeof(net_total_length), MSG_WAITALL) <= 0) {
//         return false;
//     }
//     if (recv(sockfd, &net_chunk_size, sizeof(net_chunk_size), MSG_WAITALL) <= 0) {
//         return false;
//     }

//     // Convert header values from network to host order.
//     uint32_t total_length = ntohl(net_total_length);
//     uint32_t chunk_size   = ntohl(net_chunk_size);

//     data.clear();
//     data.reserve(total_length);

//     uint32_t remaining = total_length;
//     std::vector<char> buffer(chunk_size);

//     // Read the data in chunks.
//     while (remaining > 0) {
//         uint32_t to_read = std::min(chunk_size, remaining);
//         ssize_t received = recv(sockfd, buffer.data(), to_read, MSG_WAITALL);
//         if (received <= 0) {
//             return false;
//         }
//         data.append(buffer.data(), received);
//         remaining -= received;
//     }
//     return true;
// }

// std::string Session::receiveData() {
//     std::string data;
//     if (!receive_data(sockfd, data)) {
//         return "";
//     }
//     return data;
// }