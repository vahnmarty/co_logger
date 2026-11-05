
import re
import time
from datetime import datetime

import pytesseract
from PIL import Image
from windows_capture import WindowsCapture

from PySide6.QtCore import QThread, Signal


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class MonitorWorker(QThread):

    death_detected = Signal(str, str, str)
    chat_detected = Signal(str, str, str, str)
    error_occurred = Signal(str)

    def __init__(
        self,
        window_handle,
        characters,
        chat_region
    ):
        super().__init__()

        self.window_handle = window_handle
        self.characters = characters
        self.chat_region = chat_region

        self.running = True
        self.paused = False

        self.scan_interval = 1.0
        self.last_scan = 0

        self.recent_deaths = {}
        self.recent_chats = {}

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False

    # ======================================
    # DEATH DETECTION
    # ======================================

    def detect_death(self, line):

        for character in self.characters:

            pattern = (
                rf"\b{re.escape(character)}\s+"
                rf"was\s+killed\s+by\s+([A-Za-z0-9_]+)"
            )

            match = re.search(
                pattern,
                line,
                re.IGNORECASE
            )

            if match:
                return character, match.group(1)

        return None

    # ======================================
    # CHAT DETECTION
    # ======================================

    def detect_chat(self, line):

        for character in self.characters:

            pattern = (
                rf"\b{re.escape(character)}\s+"
                rf"speaks\s+to\s+(.+?)\s*:\s*(.+)"
            )

            match = re.search(
                pattern,
                line,
                re.IGNORECASE
            )

            if match:

                return (
                    character,
                    match.group(1).strip(),
                    match.group(2).strip()
                )

        return None

    # ======================================
    # IMAGE PROCESSING
    # ======================================

    def process_chat(self, image_path):

        image = Image.open(image_path)

        x1, y1, x2, y2 = self.chat_region

        # Crop only the selected chat rectangle.
        chat = image.crop((
            x1,
            y1,
            x2,
            y2
        ))

        if chat.width <= 0 or chat.height <= 0:
            raise ValueError(
                "Invalid chat region dimensions."
            )

        # Enlarge for better OCR.
        chat = chat.resize((
            chat.width * 2,
            chat.height * 2
        ))

        text = pytesseract.image_to_string(
            chat,
            config="--psm 6"
        )

        now = time.time()

        # Remove old duplicate entries.
        for cache in [
            self.recent_deaths,
            self.recent_chats
        ]:

            for key in list(cache):

                if now - cache[key] > 30:
                    del cache[key]

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            # DEATH DETECTION
            death = self.detect_death(line)

            if death:

                character, killer = death

                key = (
                    character.lower(),
                    killer.lower()
                )

                if key not in self.recent_deaths:

                    self.recent_deaths[key] = now

                    timestamp = datetime.now().strftime(
                        "%H:%M:%S"
                    )

                    self.death_detected.emit(
                        character,
                        killer,
                        timestamp
                    )

                continue

            # CHAT DETECTION
            chat_result = self.detect_chat(line)

            if chat_result:

                character, recipient, message = chat_result

                key = (
                    character.lower(),
                    recipient.lower(),
                    message.lower()
                )

                if key not in self.recent_chats:

                    self.recent_chats[key] = now

                    timestamp = datetime.now().strftime(
                        "%H:%M:%S"
                    )

                    self.chat_detected.emit(
                        character,
                        recipient,
                        message,
                        timestamp
                    )

    # ======================================
    # CAPTURE THREAD
    # ======================================

    def run(self):

        try:

            capture = WindowsCapture(
                cursor_capture=False,
                draw_border=False,
                window_hwnd=self.window_handle
            )

            @capture.event
            def on_frame_arrived(frame, capture_control):

                if not self.running:
                    capture_control.stop()
                    return

                if self.paused:
                    return

                now = time.monotonic()

                if now - self.last_scan < self.scan_interval:
                    return

                self.last_scan = now

                frame.save_as_image(
                    "latest_capture.png"
                )

                self.process_chat(
                    "latest_capture.png"
                )

            @capture.event
            def on_closed():
                pass

            capture.start()

        except Exception as error:

            self.error_occurred.emit(str(error))
