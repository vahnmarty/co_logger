
import os
import win32gui
import pytesseract

from PIL import Image
from windows_capture import WindowsCapture

# ======================================
# CONFIGURATION
# ======================================

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Client 1 - Dubu
# Update this if the HWND changes in AC Monitor.
GAME_HWND = 23146094

OUTPUT_FILE = "wgc_capture.png"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ======================================
# CHECK TARGET WINDOW
# ======================================

if not win32gui.IsWindow(GAME_HWND):
    raise SystemExit(
        f"Invalid window handle: {GAME_HWND}\n"
        "Refresh AC Monitor and check the HWND."
    )

title = win32gui.GetWindowText(GAME_HWND)

print("Target window:", title)
print("HWND:", GAME_HWND)
print("Starting Windows Graphics Capture...")

# ======================================
# CAPTURE WINDOW
# ======================================

capture = WindowsCapture(
    cursor_capture=False,
    draw_border=False,
    window_hwnd=GAME_HWND,
)

frame_received = False


@capture.event
def on_frame_arrived(frame, capture_control):
    global frame_received

    if frame_received:
        return

    frame_received = True

    print("\nFrame received!")
    print("Resolution:", frame.width, "x", frame.height)

    # Save screenshot
    frame.save_as_image(OUTPUT_FILE)

    print("Screenshot saved:", OUTPUT_FILE)

    # Stop after first frame
    capture_control.stop()


@capture.event
def on_closed():
    print("Capture session closed.")


# Start capture
capture.start()

# ======================================
# OCR
# ======================================

if not os.path.exists(OUTPUT_FILE):
    raise SystemExit(
        "No screenshot was captured. "
        "Check the capture errors above."
    )

image = Image.open(OUTPUT_FILE)

text = pytesseract.image_to_string(image)

print("\n========== OCR RESULT ==========")
print(text)
print("================================")
