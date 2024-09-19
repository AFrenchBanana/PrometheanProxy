#include <stdio.h>
#include <string.h>


// Function to reverse a string
char* reverseString(char str[]) {
    int length = strlen(str);  // Find length of string
    int start = 0; // Initialize start index
    int end = length - 1; // Initialize end index
    while (start < end) { // Swap characters until the start and end meet
        // Swap characters at start and end
        char temp = str[start]; 
        str[start] = str[end];
        str[end] = temp;
        // Move towards the center
        start++;
        end--;
    }
    return str;
}