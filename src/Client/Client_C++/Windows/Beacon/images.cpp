#include <windows.h>
#include <gdiplus.h>
#include <string>

#pragma comment (lib,"Gdiplus.lib")

void CapturePhoto(const std::wstring& filename) {
    // Initialize GDI+
    Gdiplus::GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken;
    Gdiplus::GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, nullptr);

    // Get the screen device context
    HDC hScreenDC = GetDC(nullptr);
    HDC hMemoryDC = CreateCompatibleDC(hScreenDC);

    // Get screen dimensions
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);

    // Create a compatible bitmap
    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, width, height);
    HGDIOBJ hOldBitmap = SelectObject(hMemoryDC, hBitmap);

    // Copy the screen to the bitmap
    BitBlt(hMemoryDC, 0, 0, width, height, hScreenDC, 0, 0, SRCCOPY);

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