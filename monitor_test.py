
import time
import re
from datetime import datetime

import win32gui
from windows_capture import WindowsCapture
from PIL import Image
import pytesseract


# CONFIGURATION
WINDOW_HANDLE = 23146094  # Replace if your HWND changes

CHARACTERS = ["Dubu", "KimDahyun"]

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

SCAN_INTERVAL = 1.0  # Scan once per second

last_scan = 0
recent_deaths = {}


def detect_death(line):
    for character in CHARACTERS:
        pattern = (
            rf"\b{re.escape(character)}\s+"
            rf"was\s+killed\s+by\s+([A-Za-z0-9_]+)"
        )

        match = re.search(pattern, line, re.IGNORECASE)

        if match:
            return character, match.group(1)

    return None


def process_chat(image_path):
    image = Image.open(image_path)

    width, height = image.size

    # Bottom-left quadrant
    chat = image.crop((
        0,
        height // 2,
        width // 2,
        height
    ))

    chat = chat.resize((
        chat.width * 2,
        chat.height * 2
    ))

    text = pytesseract.image_to_string(
        chat,
        config="--psm 6"
    )

    now = time.time()

    # Remove expired entries from duplicate protection
    for key in list(recent_deaths):
        if now - recent_deaths[key] > 120:
            del recent_deaths[key]

    for line in text.splitlines():
        result = detect_death(line)

        if not result:
            continue

        character, killer = result
        key = (character.lower(), killer.lower())

        if key in recent_deaths:
            continue

        recent_deaths[key] = now

        timestamp = datetime.now().strftime("%H:%M:%S")

        print()
        print("=" * 45)
        print(f"[{timestamp}] DEATH DETECTED!")
        print(f"Character: {character}")
        print(f"Killed by: {killer}")
        print("=" * 45)


def main():
    global last_scan

    if not win32gui.IsWindow(WINDOW_HANDLE):
        print("Invalid window handle. Check WINDOW_HANDLE.")
        return

    print("AC Monitor started.")
    print("Monitoring game chat every second.")
    print("Press CTRL+C to stop.")

    capture = WindowsCapture(
        cursor_capture=False,
        draw_border=False,
        window_hwnd=WINDOW_HANDLE
    )

    @capture.event
    def on_frame_arrived(frame, capture_control):
        global last_scan

        now = time.monotonic()

        if now - last_scan < SCAN_INTERVAL:
            return

        last_scan = now

        frame.save_as_image("latest_capture.png")
        process_chat("latest_capture.png")

    @capture.event
    def on_closed():
        print("Capture session closed.")

    capture.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
