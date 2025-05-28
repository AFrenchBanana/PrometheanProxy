#include <zlib.h>
#include <cstring>
#include <stdexcept>
#include <string>
#include "logging.hpp"


std::string compressString(const std::string& str) {
    z_stream zs;
    memset(&zs, 0, sizeof(zs));
    logger.log("Starting compression of string of size: " + std::to_string(str.size()));
    if (deflateInit(&zs, Z_BEST_COMPRESSION) != Z_OK) {
        logger.error("deflateInit failed: " + std::string(zs.msg));
    }
    logger.log("Initialized zlib compression stream");
    zs.next_in = (Bytef*)str.data();
    zs.avail_in = str.size();

    int ret;
    char outbuffer[32768];
    std::string outstring;
    logger.log("Starting compression loop");
    do {
        zs.next_out = reinterpret_cast<Bytef*>(outbuffer);
        zs.avail_out = sizeof(outbuffer);

        ret = deflate(&zs, Z_FINISH);

        if (outstring.size() < zs.total_out) {
            outstring.append(outbuffer, zs.total_out - outstring.size());
        }
    } while (ret == Z_OK);
    logger.log("Compression loop finished with return code: " + std::to_string(ret));
    deflateEnd(&zs);

    if (ret != Z_STREAM_END) {
        logger.error("Compression failed with return code: " + std::to_string(ret) + " and message: " + zs.msg);
    }
    logger.log("Compression completed successfully, output size: " + std::to_string(outstring.size()));
    return outstring;
}
