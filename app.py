import sys
import re
from datetime import datetime

import pygetwindow as gw
import win32gui

from pynput import keyboard, mouse

from PySide6.QtCore import Qt, QTimer, QObject, Signal, QSize
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QTabWidget,
    QStyle,
    QScrollArea,
    QSizePolicy,
)

from monitor_worker import MonitorWorker


class HotkeyBridge(QObject):
    triggered = Signal()


class ACMonitor(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AC Monitor")
        self.setMinimumSize(680, 480)
        self.resize(760, 560)

        self.is_monitoring = False
        self.is_paused = False

        self.worker = None
        self.client_names = {}

        self.identification_windows = []
        self.identification_index = 0
        self.identification_active = False

        self.coordinate_capture_armed = False
        self.coordinate_points = []

        self.mouse_controller = mouse.Controller()
        self.ctrl_pressed = False
        self.a_pressed = False

        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.triggered.connect(
            self.capture_cursor_coordinate
        )

        self.setup_ui()
        self.refresh_clients()
        self.start_global_hotkey()

    # ======================================
    # UI
    # ======================================

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("AC Monitor")
        title.setStyleSheet(
            "font-size: 21px; font-weight: bold;"
        )

        header.addWidget(title)
        header.addStretch()

        self.start_button = self.create_icon_button(
            QStyle.StandardPixmap.SP_MediaPlay,
            "Start monitoring",
            "#198754"
        )

        self.pause_button = self.create_icon_button(
            QStyle.StandardPixmap.SP_MediaPause,
            "Pause monitoring",
            "#d99b18"
        )

        self.stop_button = self.create_icon_button(
            QStyle.StandardPixmap.SP_MediaStop,
            "Stop monitoring",
            "#dc3545"
        )

        self.start_button.clicked.connect(
            self.start_monitoring
        )
        self.pause_button.clicked.connect(
            self.pause_monitoring
        )
        self.stop_button.clicked.connect(
            self.stop_monitoring
        )

        header.addWidget(self.start_button)
        header.addWidget(self.pause_button)
        header.addWidget(self.stop_button)

        main_layout.addLayout(header)

        # STATUS
        status_layout = QHBoxLayout()
        status_layout.addStretch()

        status_layout.addWidget(QLabel("Status:"))

        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: gray;"
        )

        status_layout.addWidget(self.status_label)

        main_layout.addLayout(status_layout)

        # TABS
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(self.create_client_tab(), "Client")
        self.tabs.addTab(self.create_characters_tab(), "Characters")
        self.tabs.addTab(self.create_settings_tab(), "Settings")
        self.tabs.addTab(self.create_death_alerts_tab(), "Death Alerts")
        self.tabs.addTab(self.create_chat_log_tab(), "Chat Log")

        main_layout.addWidget(self.tabs, 1)

        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def create_icon_button(self, standard_icon, tooltip, color):

        button = QPushButton()
        button.setIcon(self.style().standardIcon(standard_icon))
        button.setIconSize(QSize(18, 18))
        button.setFixedSize(38, 34)
        button.setToolTip(tooltip)

        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                border: 1px solid white;
            }}
            QPushButton:disabled {{
                background-color: #777777;
            }}
            """
        )

        return button

    # ======================================
    # TAB: CLIENT
    # ======================================

    def create_client_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("Game Client")
        group_layout = QVBoxLayout(group)

        description = QLabel(
            "Select the Ancient Conquer game window to monitor."
        )
        description.setWordWrap(True)

        group_layout.addWidget(description)

        client_row = QHBoxLayout()

        self.client_combo = QComboBox()
        self.client_combo.setMinimumHeight(34)
        self.client_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        refresh_button = QPushButton("Refresh")
        refresh_button.setMinimumHeight(34)
        refresh_button.clicked.connect(
            self.refresh_clients
        )

        client_row.addWidget(self.client_combo, 1)
        client_row.addWidget(refresh_button)

        group_layout.addLayout(client_row)

        self.identify_button = QPushButton("Identify Clients")
        self.identify_button.setMinimumHeight(34)
        self.identify_button.clicked.connect(
            self.start_identification
        )

        group_layout.addWidget(self.identify_button)

        layout.addWidget(group)
        layout.addStretch()

        return page

    # ======================================
    # TAB: CHARACTERS
    # ======================================

    def create_characters_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Character Names")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")

        description = QLabel(
            "Enter the character names you want AC Monitor to track. "
            "Use one character name per line."
        )
        description.setWordWrap(True)

        self.character_input = QTextEdit()
        self.character_input.setPlaceholderText(
            "Dubu\nKimDahyun"
        )
        self.character_input.setMinimumHeight(250)
        self.character_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.character_input, 1)

        return page

    # ======================================
    # TAB: SETTINGS
    # ======================================

    def create_settings_tab(self):

        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ALERT CHECKBOXES
        alert_group = QGroupBox("Alert When Message Contains")
        alert_layout = QVBoxLayout(alert_group)

        self.killed_checkbox = QCheckBox("Killed")
        self.killed_checkbox.setChecked(True)

        alert_layout.addWidget(self.killed_checkbox)

        layout.addWidget(alert_group)

        # BADGE FILTERS
        badge_group = QGroupBox("Alert Badge")
        badge_layout = QHBoxLayout(badge_group)

        self.sys_checkbox = QCheckBox("Sys")
        self.talk_checkbox = QCheckBox("Talk")
        self.wrld_checkbox = QCheckBox("Wrld")
        self.no_badge_checkbox = QCheckBox("No Badge")

        for checkbox in [
            self.sys_checkbox,
            self.talk_checkbox,
            self.wrld_checkbox,
            self.no_badge_checkbox,
        ]:
            checkbox.setChecked(True)
            badge_layout.addWidget(checkbox)

        layout.addWidget(badge_group)

        # CHAT REGION
        coordinate_group = QGroupBox("Chat Log Window")
        coordinate_layout = QVBoxLayout(coordinate_group)

        instructions = QLabel(
            "Set the area of the game window where chat messages appear.\n"
            "1. Select a client in the Client tab.\n"
            "2. Click Arm Capture.\n"
            "3. Move the mouse to the top-left corner and press Ctrl+A.\n"
            "4. Move to the bottom-right corner and press Ctrl+A again."
        )
        instructions.setWordWrap(True)

        coordinate_layout.addWidget(instructions)

        coordinate_grid = QGridLayout()
        coordinate_grid.setHorizontalSpacing(10)
        coordinate_grid.setVerticalSpacing(8)

        self.x1_input = QLineEdit()
        self.y1_input = QLineEdit()
        self.x2_input = QLineEdit()
        self.y2_input = QLineEdit()

        for field in [
            self.x1_input,
            self.y1_input,
            self.x2_input,
            self.y2_input,
        ]:
            field.setReadOnly(True)
            field.setPlaceholderText("Not set")
            field.setMinimumWidth(90)
            field.setMinimumHeight(30)

        coordinate_grid.addWidget(QLabel("Left (X1)"), 0, 0)
        coordinate_grid.addWidget(self.x1_input, 0, 1)
        coordinate_grid.addWidget(QLabel("Top (Y1)"), 0, 2)
        coordinate_grid.addWidget(self.y1_input, 0, 3)

        coordinate_grid.addWidget(QLabel("Right (X2)"), 1, 0)
        coordinate_grid.addWidget(self.x2_input, 1, 1)
        coordinate_grid.addWidget(QLabel("Bottom (Y2)"), 1, 2)
        coordinate_grid.addWidget(self.y2_input, 1, 3)

        coordinate_grid.setColumnStretch(1, 1)
        coordinate_grid.setColumnStretch(3, 1)

        coordinate_layout.addLayout(coordinate_grid)

        self.coordinate_status = QLabel(
            "Coordinates not set."
        )
        self.coordinate_status.setWordWrap(True)
        self.coordinate_status.setStyleSheet("color: gray;")

        coordinate_layout.addWidget(self.coordinate_status)

        coordinate_buttons = QHBoxLayout()

        self.arm_button = QPushButton("Arm Capture")
        self.arm_button.clicked.connect(
            self.toggle_coordinate_capture
        )

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(
            self.copy_coordinates
        )

        paste_button = QPushButton("Paste")
        paste_button.clicked.connect(
            self.paste_coordinates
        )

        clear_coordinates_button = QPushButton("Clear")
        clear_coordinates_button.clicked.connect(
            self.clear_coordinates
        )

        coordinate_buttons.addWidget(self.arm_button)
        coordinate_buttons.addWidget(copy_button)
        coordinate_buttons.addWidget(paste_button)
        coordinate_buttons.addWidget(clear_coordinates_button)

        coordinate_layout.addLayout(coordinate_buttons)

        layout.addWidget(coordinate_group)
        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        return page

    # ======================================
    # TAB: DEATH ALERTS
    # ======================================

    def create_death_alerts_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText(
            "Detected deaths will appear here..."
        )
        self.log_output.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        clear_button = QPushButton("Clear Death Alerts")
        clear_button.clicked.connect(
            self.log_output.clear
        )

        layout.addWidget(self.log_output, 1)
        layout.addWidget(clear_button)

        return page

    # ======================================
    # TAB: CHAT LOG
    # ======================================

    def create_chat_log_tab(self):

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.chat_output = QTextEdit()
        self.chat_output.setReadOnly(True)
        self.chat_output.setPlaceholderText(
            "Detected chat messages will appear here..."
        )
        self.chat_output.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        clear_button = QPushButton("Clear Chat Log")
        clear_button.clicked.connect(
            self.chat_output.clear
        )

        layout.addWidget(self.chat_output, 1)
        layout.addWidget(clear_button)

        return page

    # ======================================
    # GLOBAL HOTKEY
    # ======================================

    def start_global_hotkey(self):

        self.hotkey_listener = keyboard.Listener(
            on_press=self.global_key_press,
            on_release=self.global_key_release
        )

        self.hotkey_listener.start()

    def global_key_press(self, key):

        if key in (
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_l,
            keyboard.Key.ctrl_r,
        ):
            self.ctrl_pressed = True
            return

        # Windows may report Ctrl+A as virtual key 0x41
        # instead of the character "a".
        is_a_key = (
            getattr(key, "vk", None) == 0x41
            or getattr(key, "char", None) == "a"
            or getattr(key, "char", None) == "A"
        )

        if self.ctrl_pressed and is_a_key and not self.a_pressed:
            self.a_pressed = True

            if self.coordinate_capture_armed:
                self.hotkey_bridge.triggered.emit()

    def global_key_release(self, key):

        if key in (
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_l,
            keyboard.Key.ctrl_r,
        ):
            self.ctrl_pressed = False

        is_a_key = (
            getattr(key, "vk", None) == 0x41
            or getattr(key, "char", None) in ("a", "A")
        )

        if is_a_key:
            self.a_pressed = False

    # ======================================
    # COORDINATE CAPTURE
    # ======================================

    def toggle_coordinate_capture(self):

        if self.coordinate_capture_armed:
            self.coordinate_capture_armed = False
            self.arm_button.setText("Arm Capture")
            self.coordinate_status.setText(
                "Coordinate capture cancelled."
            )
            return

        handle = self.client_combo.currentData()

        if handle is None:
            QMessageBox.warning(
                self,
                "Missing Client",
                "Select a game client first."
            )
            return

        if not win32gui.IsWindow(handle):
            QMessageBox.warning(
                self,
                "Invalid Window",
                "The selected game window is no longer valid. "
                "Click Refresh and select it again."
            )
            return

        self.coordinate_points = []
        self.coordinate_capture_armed = True

        self.x1_input.clear()
        self.y1_input.clear()
        self.x2_input.clear()
        self.y2_input.clear()

        self.arm_button.setText("Cancel Capture")

        self.coordinate_status.setText(
            "Waiting for TOP-LEFT corner. Press Ctrl+A."
        )
        self.coordinate_status.setStyleSheet(
            "color: blue; font-weight: bold;"
        )

    def capture_cursor_coordinate(self):

        if not self.coordinate_capture_armed:
            return

        handle = self.client_combo.currentData()

        if handle is None or not win32gui.IsWindow(handle):
            self.coordinate_status.setText(
                "Invalid game window. Refresh clients."
            )
            self.coordinate_capture_armed = False
            self.arm_button.setText("Arm Capture")
            return

        screen_x, screen_y = self.mouse_controller.position

        try:
            client_x, client_y = win32gui.ScreenToClient(
                handle,
                (int(screen_x), int(screen_y))
            )

        except Exception as error:
            self.coordinate_status.setText(
                f"Coordinate error: {error}"
            )
            return

        self.coordinate_points.append(
            (client_x, client_y)
        )

        if len(self.coordinate_points) == 1:

            self.x1_input.setText(str(client_x))
            self.y1_input.setText(str(client_y))

            self.coordinate_status.setText(
                f"Top-left saved: ({client_x}, {client_y}). "
                "Move to bottom-right and press Ctrl+A."
            )

        elif len(self.coordinate_points) == 2:

            self.x2_input.setText(str(client_x))
            self.y2_input.setText(str(client_y))

            self.coordinate_capture_armed = False
            self.arm_button.setText("Arm Capture")

            x1, y1 = self.coordinate_points[0]
            x2, y2 = self.coordinate_points[1]

            if x2 <= x1 or y2 <= y1:
                self.coordinate_status.setText(
                    "Invalid rectangle. Bottom-right must be "
                    "to the right and below top-left."
                )
                self.coordinate_status.setStyleSheet(
                    "color: red; font-weight: bold;"
                )
                return

            self.coordinate_status.setText(
                f"Chat area saved: {x2 - x1} x {y2 - y1} pixels."
            )
            self.coordinate_status.setStyleSheet(
                "color: green; font-weight: bold;"
            )

    def get_chat_region(self):

        try:
            x1 = int(self.x1_input.text())
            y1 = int(self.y1_input.text())
            x2 = int(self.x2_input.text())
            y2 = int(self.y2_input.text())

            if x2 <= x1 or y2 <= y1:
                return None

            return (x1, y1, x2, y2)

        except ValueError:
            return None

    def copy_coordinates(self):

        region = self.get_chat_region()

        if region is None:
            QMessageBox.warning(
                self,
                "No Coordinates",
                "Capture valid coordinates first."
            )
            return

        QApplication.clipboard().setText(
            ", ".join(map(str, region))
        )

        self.coordinate_status.setText(
            "Coordinates copied to clipboard."
        )

    def paste_coordinates(self):

        clipboard_text = QApplication.clipboard().text()

        numbers = re.findall(
            r"-?\d+",
            clipboard_text
        )

        if len(numbers) != 4:
            QMessageBox.warning(
                self,
                "Invalid Clipboard",
                "Clipboard must contain four numbers: "
                "X1, Y1, X2, Y2."
            )
            return

        x1, y1, x2, y2 = map(int, numbers)

        if x2 <= x1 or y2 <= y1:
            QMessageBox.warning(
                self,
                "Invalid Coordinates",
                "Bottom-right must be right and below top-left."
            )
            return

        self.x1_input.setText(str(x1))
        self.y1_input.setText(str(y1))
        self.x2_input.setText(str(x2))
        self.y2_input.setText(str(y2))

        self.coordinate_points = [
            (x1, y1),
            (x2, y2)
        ]

        self.coordinate_status.setText(
            "Coordinates pasted successfully."
        )
        self.coordinate_status.setStyleSheet(
            "color: green;"
        )

    def clear_coordinates(self):

        self.coordinate_points = []
        self.coordinate_capture_armed = False

        self.x1_input.clear()
        self.y1_input.clear()
        self.x2_input.clear()
        self.y2_input.clear()

        self.arm_button.setText("Arm Capture")

        self.coordinate_status.setText(
            "Coordinates not set."
        )
        self.coordinate_status.setStyleSheet(
            "color: gray;"
        )

    # ======================================
    # CLIENT WINDOW DISCOVERY
    # ======================================

    def get_game_windows(self):

        windows = []

        for window in gw.getAllWindows():

            title = window.title.strip()

            if not title:
                continue

            if window.width <= 200 or window.height <= 100:
                continue

            title_lower = title.lower()

            if (
                "ancient" not in title_lower
                and "conquer" not in title_lower
            ):
                continue

            windows.append(window)

        return windows

    def refresh_clients(self):

        selected_handle = self.client_combo.currentData()

        self.client_combo.clear()

        windows = self.get_game_windows()

        for index, window in enumerate(windows, start=1):

            handle = window._hWnd
            character = self.client_names.get(handle)

            if character:
                label = f"Client {index} - {character}"
            else:
                label = f"Client {index} - Unidentified"

            label += f" (HWND: {handle})"

            self.client_combo.addItem(label, handle)

        if self.client_combo.count() == 0:
            self.client_combo.addItem(
                "No Ancient Conquer windows found"
            )

        if selected_handle is not None:
            index = self.client_combo.findData(selected_handle)

            if index >= 0:
                self.client_combo.setCurrentIndex(index)

    # ======================================
    # IDENTIFY CLIENTS
    # ======================================

    def start_identification(self):

        if self.is_monitoring:
            QMessageBox.warning(
                self,
                "Monitoring Active",
                "Stop monitoring before identifying clients."
            )
            return

        self.identification_windows = self.get_game_windows()

        if not self.identification_windows:
            QMessageBox.warning(
                self,
                "No Clients Found",
                "No Ancient Conquer windows were found."
            )
            return

        self.identification_index = 0
        self.identification_active = True

        self.identify_button.setEnabled(False)

        self.set_status("Starting identification...", "blue")

        self.identify_next_client()

    def identify_next_client(self):

        if not self.identification_active:
            return

        if self.identification_index >= len(self.identification_windows):
            self.finish_identification()
            return

        window = self.identification_windows[
            self.identification_index
        ]

        client_number = self.identification_index + 1

        try:
            if window.isMinimized:
                window.restore()

            window.activate()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Window Activation Failed",
                str(error)
            )

        self.set_status(
            f"Identifying Client {client_number}...",
            "blue"
        )

        QTimer.singleShot(4000, self.ask_client_name)

    def ask_client_name(self):

        if not self.identification_active:
            return

        window = self.identification_windows[
            self.identification_index
        ]

        client_number = self.identification_index + 1
        handle = window._hWnd

        self.showNormal()
        self.raise_()
        self.activateWindow()

        character, accepted = QInputDialog.getText(
            self,
            f"Identify Client {client_number}",
            f"Which character is logged into Client "
            f"{client_number}?\nEnter the character name:"
        )

        if not accepted:
            self.identification_active = False
            self.finish_identification()
            return

        character = character.strip()

        if character:
            self.client_names[handle] = character

        self.identification_index += 1

        QTimer.singleShot(300, self.identify_next_client)

    def finish_identification(self):

        self.identification_active = False
        self.identify_button.setEnabled(True)

        self.refresh_clients()

        self.set_status("Identification Complete", "green")

        QMessageBox.information(
            self,
            "Identification Complete",
            "Client identification finished."
        )

    # ======================================
    # MONITORING CONTROLS
    # ======================================

    def start_monitoring(self):

        if self.worker is not None and self.worker.isRunning():
            return

        client = self.client_combo.currentText()
        handle = self.client_combo.currentData()

        if handle is None or not win32gui.IsWindow(handle):
            QMessageBox.warning(
                self,
                "Invalid Client",
                "Refresh and select a valid game client."
            )
            self.tabs.setCurrentIndex(0)
            return

        characters = [
            name.strip()
            for name in self.character_input.toPlainText().splitlines()
            if name.strip()
        ]

        if not characters:
            QMessageBox.warning(
                self,
                "Missing Characters",
                "Enter at least one character name."
            )
            self.tabs.setCurrentIndex(1)
            return

        if not self.killed_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Missing Alert",
                "Please select Killed."
            )
            self.tabs.setCurrentIndex(2)
            return

        badges = [
            self.sys_checkbox,
            self.talk_checkbox,
            self.wrld_checkbox,
            self.no_badge_checkbox,
        ]

        if not any(box.isChecked() for box in badges):
            QMessageBox.warning(
                self,
                "Missing Badge",
                "Select at least one badge filter."
            )
            self.tabs.setCurrentIndex(2)
            return

        chat_region = self.get_chat_region()

        if chat_region is None:
            QMessageBox.warning(
                self,
                "Chat Area Not Set",
                "Please capture the chat log coordinates first."
            )
            self.tabs.setCurrentIndex(2)
            return

        self.worker = MonitorWorker(
            window_handle=handle,
            characters=characters,
            chat_region=chat_region
        )

        self.worker.death_detected.connect(
            self.on_death_detected
        )

        self.worker.chat_detected.connect(
            self.on_chat_detected
        )

        self.worker.error_occurred.connect(
            self.on_monitor_error
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        self.is_monitoring = True
        self.is_paused = False

        self.set_status("Monitoring", "green")

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        self.pause_button.setToolTip("Pause monitoring")

        self.log_output.append(
            f"[{self.current_time()}] Started monitoring: {client}"
        )

        self.worker.start()

    def pause_monitoring(self):

        if not self.is_monitoring or self.worker is None:
            return

        self.is_paused = not self.is_paused

        if self.is_paused:
            self.worker.pause()

            self.set_status("Paused", "#d99b18")
            self.pause_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_MediaPlay
                )
            )
            self.pause_button.setToolTip("Resume monitoring")

            self.log_output.append(
                f"[{self.current_time()}] Monitoring paused."
            )

        else:
            self.worker.resume()

            self.set_status("Monitoring", "green")
            self.pause_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_MediaPause
                )
            )
            self.pause_button.setToolTip("Pause monitoring")

            self.log_output.append(
                f"[{self.current_time()}] Monitoring resumed."
            )

    def stop_monitoring(self):

        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()

        self.is_monitoring = False
        self.is_paused = False

        self.set_status("Stopping...", "#d99b18")

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    # ======================================
    # MONITOR EVENTS
    # ======================================

    def on_death_detected(self, character, killer, timestamp):

        message = (
            f"[{timestamp}] DEATH DETECTED\n"
            f"{character} was killed by {killer}"
        )

        self.log_output.append(message)
        print(message)

    def on_chat_detected(
        self,
        character,
        recipient,
        message,
        timestamp
    ):

        entry = (
            f"[{timestamp}] {character} -> {recipient}\n"
            f"{message}"
        )

        self.chat_output.append(entry)
        print(entry)

    def on_monitor_error(self, error):

        self.log_output.append(
            f"[{self.current_time()}] ERROR: {error}"
        )

        QMessageBox.critical(
            self,
            "Monitoring Error",
            error
        )

    def on_worker_finished(self):

        self.is_monitoring = False
        self.is_paused = False

        self.set_status("Stopped", "red")

        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.pause_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MediaPause
            )
        )
        self.pause_button.setToolTip("Pause monitoring")

        self.log_output.append(
            f"[{self.current_time()}] Monitoring stopped."
        )

        self.worker = None

    # ======================================
    # HELPERS
    # ======================================

    def set_status(self, text, color):

        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"font-weight: bold; color: {color};"
        )

    def current_time(self):

        return datetime.now().strftime("%H:%M:%S")

    # ======================================
    # APPLICATION CLOSE
    # ======================================

    def closeEvent(self, event):

        self.coordinate_capture_armed = False

        if hasattr(self, "hotkey_listener"):
            self.hotkey_listener.stop()

        if self.worker is not None and self.worker.isRunning():

            self.worker.stop()

            if not self.worker.wait(3000):
                QMessageBox.warning(
                    self,
                    "Monitor Still Stopping",
                    "The capture worker is still stopping. "
                    "Please wait a moment and close again."
                )

                event.ignore()
                return

        event.accept()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ACMonitor()
    window.show()

    sys.exit(app.exec())