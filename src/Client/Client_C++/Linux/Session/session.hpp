#ifndef SESSION_HPP
#define SESSION_HPP

#include <string>
#include <thread>
#include <vector>
#include <openssl/ssl.h>

class Session {
public:
    Session();
    ~Session();

    // One-time global OpenSSL initialization/cleanup.
    static void initSSL();
    static void cleanupSSL();

    // Initialize the TLS context and socket.
    bool socketInitialization();

    // Continuously attempts connection until successful.
    bool connection();

    // Listens for incoming messages and spawns a listener thread.
    void checkListener();

    // Sends data over the TLS connection.
    bool sendData(const std::string &data);

    // Low-level send with header and chunked transmission on a raw socket.
    bool send_data(int sockfd, const std::string &data);

    // Low-level receive that expects an 8-byte header (total length and chunk size),
    // then reads data in chunks. Uses the provided socket.
    bool receive_data(int sockfd, std::string &data);

    // Convenience method to receive data from the member socket.
    std::string receiveData();

private:
    SSL_CTX *ctx;
    SSL     *ssl;
    int      sockfd;
    std::thread listenerThread;
};

#endif // SESSION_HPP