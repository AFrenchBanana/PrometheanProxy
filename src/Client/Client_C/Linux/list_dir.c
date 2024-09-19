#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dirent.h>
#include <unistd.h>
#include <pwd.h>
#include <grp.h>
#include <time.h>
#include <string.h>
#include <openssl/ssl.h>

#ifndef S_ISVTX
#define S_ISVTX  01000 // Sticky bit: not supported
#define PATH_MAX 4096 // Choose a reasonable value if PATH_MAX is not defined
#endif




#include "../Generic/send_receive.h"

// Function to convert permission bits to human-readable format
char *get_permissions(mode_t mode) {
    static char permissions[11] = "-rwxrwxrwx";

    // Check owner permissions
    permissions[1] = (mode & S_IRUSR) ? 'r' : '-';
    permissions[2] = (mode & S_IWUSR) ? 'w' : '-';
    permissions[3] = (mode & S_IXUSR) ? (mode & S_ISUID) ? 's' : 'x' : '-';

    // Check group permissions
    permissions[4] = (mode & S_IRGRP) ? 'r' : '-';
    permissions[5] = (mode & S_IWGRP) ? 'w' : '-';
    permissions[6] = (mode & S_IXGRP) ? (mode & S_ISGID) ? 's' : 'x' : '-';

    // Check other permissions
    permissions[7] = (mode & S_IROTH) ? 'r' : '-';
    permissions[8] = (mode & S_IWOTH) ? 'w' : '-';
    permissions[9] = (mode & S_IXOTH) ? (mode & S_ISVTX) ? 't' : 'x' : '-';

    return permissions;
}

// Function to check if the client has permission to access the directory
int has_permission(const char *directory_path) {
    return access(directory_path, R_OK | X_OK) == 0; // Check read and execute permissions
}

void listdir(SSL *ssl) {
    DIR *dir;
    struct dirent *entry;
    char *requested_dir = receive_data(ssl);
    if (requested_dir == NULL) {
        send_data(ssl, "Error: received data is NULL");
        return;
    }
    printf("dir is %s\n", requested_dir);

    // Check if client has permission to access the directory
    if (!has_permission(requested_dir)) {
        send_data(ssl, "Permission denied / dir does not exist");
        return;
    }

    dir = opendir(requested_dir);
    if (dir == NULL) {
        send_data(ssl, "Failed to open directory");
        return;
    }

    // Initialize buffer with reasonable initial size
    size_t buffer_size = 4096;
    char *buffer = (char *)malloc(buffer_size);
    if (buffer == NULL) {
        send_data(ssl, "Memory allocation error");
        closedir(dir);
        return;
    }

    // Ensure buffer starts as an empty string
    buffer[0] = '\0';
    size_t current_length = 0;

    while ((entry = readdir(dir)) != NULL) {
        char *file_name = entry->d_name;
        struct stat file_stat;

        // Construct full path to file
        char full_path[PATH_MAX];
        snprintf(full_path, PATH_MAX, "%s/%s", requested_dir, file_name);

        // Get file metadata and handle potential errors
        if (stat(full_path, &file_stat) != 0) {
            continue;
        }

        // Get file permissions in octal format
        char permissions[11];
        snprintf(permissions, sizeof(permissions), "%s", get_permissions(file_stat.st_mode));

        if (S_ISDIR(file_stat.st_mode)) {
            permissions[0] = 'd';
        }

        // Get user and group information (optional)
        struct passwd *pw = getpwuid(file_stat.st_uid);
        struct group *gr = getgrgid(file_stat.st_gid);
        char *user_name = pw ? pw->pw_name : "unknown";
        char *group_name = gr ? gr->gr_name : "unknown";

        // Get formatted time (adjust format as needed)
        char formatted_time[32];
        strftime(formatted_time, sizeof(formatted_time), "%b %d %H:%M", localtime(&file_stat.st_mtime));

        // Format entry details
        size_t info_length = snprintf(NULL, 0,
                                      "%s %ld %s %s %lld %.12s %s\n",
                                      permissions, // File permissions
                                      (long)file_stat.st_nlink,  // Number of hard links
                                      user_name,
                                      group_name,
                                      (long long)file_stat.st_size, // File size
                                      formatted_time + 4,  // Skip the day of the week
                                      file_name);

        // Check and resize buffer if needed
        if (current_length + info_length + 1 > buffer_size) {
            buffer_size = buffer_size * 2 + info_length; // Adjust growth factor as needed
            char *new_buffer = (char *)realloc(buffer, buffer_size);
            if (new_buffer == NULL) {
                send_data(ssl, "Memory allocation error");
                closedir(dir);
                free(buffer);
                return;
            }
            buffer = new_buffer;
        }

        // Concatenate formatted entry details to the buffer
        char entry_details[info_length + 1];
        snprintf(entry_details, sizeof(entry_details),
                 "%s %ld %s %s %lld %.12s %s\n",
                 permissions, // File permissions
                 (long)file_stat.st_nlink,  // Number of hard links
                 user_name,
                 group_name,
                 (long long)file_stat.st_size, // File size
                 formatted_time + 4,  // Skip the day of the week
                 file_name);
        strcat(buffer, entry_details);
        current_length += info_length;
    }

    closedir(dir);
    send_data(ssl, buffer);

    // Free the allocated buffer
    free(buffer);
}

