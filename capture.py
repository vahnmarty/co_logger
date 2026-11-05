
import ctypes
import pygetwindow as gw
import win32gui
import win32ui

from PIL import Image
import pytesseract

# Tesseract location
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Windows API
user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.PrintWindow.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint
]
user32.PrintWindow.restype = ctypes.c_bool

# Find Ancient Conquer windows
windows = []

for window in gw.getAllWindows():

    title = window.title.strip()

    if (
        title
        and ("ancient" in title.lower() or "conquer" in title.lower())
        and window.width > 200
        and window.height > 100
    ):
        windows.append(window)

print(f"Found {len(windows)} game windows.")

if not windows:
    raise SystemExit("No game windows found.")

# Select first client
game = windows[0]

print("Selected:", game.title)
print("HWND:", game._hWnd)

hwnd = game._hWnd

left, top, right, bottom = win32gui.GetWindowRect(hwnd)

width = right - left
height = bottom - top

print(f"Window size: {width} x {height}")

# Get window device context
window_dc = win32gui.GetWindowDC(hwnd)

dc_obj = win32ui.CreateDCFromHandle(window_dc)
memory_dc = dc_obj.CreateCompatibleDC()

bitmap = win32ui.CreateBitmap()
bitmap.CreateCompatibleBitmap(dc_obj, width, height)

memory_dc.SelectObject(bitmap)

# Capture using Windows PrintWindow API
result = user32.PrintWindow(
    hwnd,
    memory_dc.GetSafeHdc(),
    2
)

print("PrintWindow result:", result)

# Convert bitmap to Pillow image
bitmap_info = bitmap.GetInfo()
bitmap_data = bitmap.GetBitmapBits(True)

image = Image.frombuffer(
    "RGB",
    (bitmap_info["bmWidth"], bitmap_info["bmHeight"]),
    bitmap_data,
    "raw",
    "BGRX",
    0,
    1
).copy()

# Save screenshot
image.save("capture_test.png")

# Release Windows resources
win32gui.DeleteObject(bitmap.GetHandle())
memory_dc.DeleteDC()
dc_obj.DeleteDC()
win32gui.ReleaseDC(hwnd, window_dc)

print("Screenshot saved: capture_test.png")

# OCR test
text = pytesseract.image_to_string(image)

print("\nRecognized text:")
print(text)
