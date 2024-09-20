#include <openssl/ssl.h>

int send_header(SSL* , uint32_t , uint32_t );
void send_data(SSL* , const char* );
char* receive_data(SSL*);
