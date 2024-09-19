#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdint.h>
#include <openssl/ssl.h>


#include "Generic/send_receive.h"
#include "Linux/socket.h"
#include "Generic/string_manipulation.h"
#include "Linux/systeminfo.h"
#include "Generic/server_handler.h"
#include "Generic/hash_file.h"


int main() {
    while(true) {
        SSL* ssl = ssl_connection();
        if (ssl == NULL) {
            return EXIT_FAILURE;
        }
        authentication();
        char* hostname = get_hostname();
        send_data(ssl, hostname);
        //free(hostname);
        char* sniffer_dummy = receive_data(ssl);
        free(sniffer_dummy);
        server_handler(ssl);
        close(SSL_get_fd(ssl));
    }
}
