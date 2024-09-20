#include <openssl/ssl.h>

SSL* ssl_connection(int PORT, char* SOCK_ADDRESS);
void authentication(void);
char* get_hostname(void);

