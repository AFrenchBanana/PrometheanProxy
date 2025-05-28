
#ifdef __unix__
#include "../../Linux/Session/session.hpp"
#include "../../Linux/generic.hpp"
#elif defined(_WIN32)
#include "../../Windows/Session/session.hpp"
#include "../../Windows/generic.hpp"
#endif

#include "../../Generic/config.hpp"
#include "../../Generic/logging.hpp"


bool sessionHandler(){ 
    logger.log("Entering the server handler");
    while (true) {
        logger.warn("not implemented yet returning");
        return true;
    }   

}

bool sessionConnect() {
    Session session("127.0.0.1", 2000);
    if (session.connectToServer()) {
        std::string authkey = session.receiveData();
        logger.log("Received authentication key: " + authkey);
        std::string auth_response = session.authentication(authkey);
        logger.log("Authentication response: " + auth_response);
        if (!session.sendData(auth_response)) {
            logger.error("Failed to send authentication response");
            return 0;
        }
        logger.log("Authentication response sent successfully");
        std::string hostname =  getHostname();
        if (!session.sendData(hostname)) {
            logger.warn("Couldnt not send hostname");
            return 0;
        };
        if (!session.sendData(OS + ", " + ID)) {
            logger.warn("Couldnt send OS and UID");
            return 0;
        }; 
        logger.log("Sending OS and Mode");
        std::string _ = session.receiveData(); //place holder for shark reader
        sessionHandler();
        return true;
    } else {
        logger.error("Couldnt not connect to the server");
        return false;
    }
};

