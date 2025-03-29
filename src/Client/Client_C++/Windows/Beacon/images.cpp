#include <windows.h>
#include <gdiplus.h>
#include <string>
#include "../../../../Generic/logging.hpp"

#pragma comment (lib,"Gdiplus.lib")

// Define the minimum supported version (Windows Vista or later)
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600 // Windows Vista
#endif

void CapturePhoto(const std::wstring& filename) {
    // Check if SetProcessDPIAware is available
    HMODULE hUser32 = LoadLibrary(TEXT("user32.dll"));
    if (hUser32) {
        typedef BOOL (WINAPI *LPFNSETPROCESSDPIAWARE)(void);
        LPFNSETPROCESSDPIAWARE pSetProcessDPIAware = (LPFNSETPROCESSDPIAWARE)GetProcAddress(hUser32, "SetProcessDPIAware");
        if (pSetProcessDPIAware) {
            pSetProcessDPIAware();
        }
        FreeLibrary(hUser32);
    }

    // Initialize GDI+
    Gdiplus::GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken;
    Gdiplus::GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, nullptr);

    // Get the screen device context
    HDC hScreenDC = GetDC(nullptr);
    HDC hMemoryDC = CreateCompatibleDC(hScreenDC);

    // Get screen dimensions for all monitors
    int width = GetSystemMetrics(SM_CXVIRTUALSCREEN);
    int height = GetSystemMetrics(SM_CYVIRTUALSCREEN);
    int left = GetSystemMetrics(SM_XVIRTUALSCREEN);
    int top = GetSystemMetrics(SM_YVIRTUALSCREEN);

    // Create a compatible bitmap with the correct width and height
    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, width, height);
    if (!hBitmap) {
        ReleaseDC(nullptr, hScreenDC);
        log_error("Failed to create compatible bitmap.");
        return;
        return;
    }

    HGDIOBJ hOldBitmap = SelectObject(hMemoryDC, hBitmap);

    // Set proper scaling
    SetGraphicsMode(hMemoryDC, GM_ADVANCED);
    SetStretchBltMode(hMemoryDC, HALFTONE);

    // Copy the screen to the bitmap, ensuring we capture from the correct position
    if (!BitBlt(hMemoryDC, 0, 0, width, height, hScreenDC, left, top, SRCCOPY)) {
        // Handle error
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(nullptr, hScreenDC);
        return;
    }

    // Initialize GDI+ Bitmap from HBITMAP
    Gdiplus::Bitmap bitmap(hBitmap, nullptr);

    // Save the bitmap to a file
    CLSID clsid;
    CLSIDFromString(L"{557CF400-1A04-11D3-9A73-0000F81EF32E}", &clsid); // CLSID for PNG encoder
    bitmap.Save(filename.c_str(), &clsid, nullptr);

    // Cleanup
    SelectObject(hMemoryDC, hOldBitmap);
    DeleteObject(hBitmap);
    DeleteDC(hMemoryDC);
    ReleaseDC(nullptr, hScreenDC);
    Gdiplus::GdiplusShutdown(gdiplusToken);
}
