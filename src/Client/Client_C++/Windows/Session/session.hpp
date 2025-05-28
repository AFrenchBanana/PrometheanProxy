#ifndef SESSION_HPP
#define SESSION_HPP

#include <openssl/ssl.h>
#include <string>
#include <vector>
#include <iostream>
#include <winsock2.h>

class Session {
public:
    Session(const std::string &serverAddress, int port);
    bool connectToServer();
    void disconnect();
    bool sendData(const std::string &data);
    std::string receiveData();
    std::string authentication(const std::string &auth_key); 
private:
    std::string serverAddress;
    int port;
    SOCKET sock;
    SSL_CTX* ctx;
    SSL* ssl;

    void initOpenSSL();
    bool initWinsock();
    bool createSocket();
    bool connectSocket();
    void cleanup();
};

#endif