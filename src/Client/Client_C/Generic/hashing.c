#include <openssl/evp.h>
#include <string.h>


// SHA512 hash function 
void sha512(const char *input, char *output) {
    EVP_MD_CTX *mdctx; 
    const EVP_MD *md; 
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int hash_len;
    md = EVP_sha512();
    mdctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(mdctx, md, NULL);
    EVP_DigestUpdate(mdctx, input, strlen(input));
    EVP_DigestFinal_ex(mdctx, hash, &hash_len);
    EVP_MD_CTX_free(mdctx);
    for (int i = 0; i < hash_len; i++) {
        sprintf(output + (i * 2), "%02x", hash[i]);
    }
    output[hash_len * 2] = '\0';
}



void sha256(const char *input, char *output, int output_size) {
  EVP_MD_CTX *mdctx; 
  const EVP_MD *md; 
  unsigned char hash[EVP_MAX_MD_SIZE];
  unsigned int hash_len;
  md = EVP_sha256();
  mdctx = EVP_MD_CTX_new();
  EVP_DigestInit_ex(mdctx, md, NULL);
  EVP_DigestUpdate(mdctx, input, strlen(input));
  EVP_DigestFinal_ex(mdctx, hash, &hash_len);
  EVP_MD_CTX_free(mdctx);

  // Use snprintf with maximum output size to prevent buffer overflows
  int i;
  for (i = 0; i < hash_len && i < output_size - 1; i++) {
    snprintf(output + (i * 2), output_size - (i * 2), "%02x", hash[i]);
  }
  output[i * 2] = '\0';
}
