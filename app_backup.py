
import sys
import pygetwindow as gw

import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QInputDialog,
)


class ACMonitor(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AC Monitor")
        self.setMinimumSize(440, 620)
        self.resize(480, 680)

        self.is_monitoring = False
        self.is_paused = False

        # Window handle -> assigned character name
        self.client_names = {}

        # Client identification process
        self.identification_windows = []
        self.identification_index = 0
        self.identification_active = False

        self.setup_ui()
        self.refresh_clients()

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # HEADER
        title = QLabel("AC Monitor")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")

        subtitle = QLabel("Ancient Conquer Character Monitor")
        subtitle.setStyleSheet("color: gray;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # CLIENT SELECTION
        client_group = QGroupBox("Game Client")
        client_layout = QVBoxLayout(client_group)

        client_row = QHBoxLayout()

        self.client_combo = QComboBox()
        self.client_combo.setMinimumHeight(36)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_clients)

        client_row.addWidget(self.client_combo)
        client_row.addWidget(refresh_button)

        self.identify_button = QPushButton("Identify Clients")
        self.identify_button.clicked.connect(
            self.start_identification
        )

        client_layout.addLayout(client_row)
        client_layout.addWidget(self.identify_button)

        layout.addWidget(client_group)

        # CHARACTER NAMES
        character_group = QGroupBox("Character Names")
        character_layout = QVBoxLayout(character_group)

        info = QLabel("Enter one character name per line:")

        self.character_input = QTextEdit()
        self.character_input.setPlaceholderText(
            "Dubu\nKimDahyun\nAnotherCharacter"
        )
        self.character_input.setMinimumHeight(110)

        character_layout.addWidget(info)
        character_layout.addWidget(self.character_input)

        layout.addWidget(character_group)

        # DEATH ALERT
        alert_group = QGroupBox("Alert When Message Contains")
        alert_layout = QVBoxLayout(alert_group)

        self.killed_checkbox = QCheckBox("Killed")
        self.killed_checkbox.setChecked(True)

        alert_layout.addWidget(self.killed_checkbox)
        layout.addWidget(alert_group)

        # BADGE FILTERS
        badge_group = QGroupBox("Alert Badge")
        badge_layout = QVBoxLayout(badge_group)

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

        # STATUS
        status_group = QGroupBox("Monitoring Status")
        status_layout = QHBoxLayout(status_group)

        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: gray;"
        )

        status_layout.addWidget(QLabel("Status:"))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_group)

        # BUTTONS
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        self.start_button.clicked.connect(self.start_monitoring)
        self.pause_button.clicked.connect(self.pause_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)

        self.start_button.setStyleSheet(
            "background-color: #198754; color: white; "
            "padding: 10px; font-weight: bold;"
        )

        self.pause_button.setStyleSheet(
            "background-color: #d99b18; color: white; "
            "padding: 10px; font-weight: bold;"
        )

        self.stop_button.setStyleSheet(
            "background-color: #dc3545; color: white; "
            "padding: 10px; font-weight: bold;"
        )

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        layout.addStretch()

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

            # Only include Ancient Conquer windows
            title_lower = title.lower()

            if "ancient" not in title_lower and "conquer" not in title_lower:
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
            self.client_combo.addItem("No Ancient Conquer windows found")

        # Preserve selection when refreshing
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
                "No Ancient Conquer windows were found.\n\n"
                "Make sure the game window titles contain "
                "'Ancient' or 'Conquer'."
            )
            return

        self.identification_index = 0
        self.identification_active = True

        self.identify_button.setEnabled(False)
        self.status_label.setText("Starting identification...")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: blue;"
        )

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
                f"Could not activate Client {client_number}.\n\n"
                f"{error}"
            )

        self.status_label.setText(
            f"Identifying Client {client_number} "
            f"of {len(self.identification_windows)}..."
        )

        # Give yourself 4 seconds to see the game character
        QTimer.singleShot(4000, self.ask_client_name)

    def ask_client_name(self):

        if not self.identification_active:
            return

        window = self.identification_windows[
            self.identification_index
        ]

        client_number = self.identification_index + 1
        handle = window._hWnd

        # Bring AC Monitor back to the foreground
        self.showNormal()
        self.raise_()
        self.activateWindow()

        character, accepted = QInputDialog.getText(
            self,
            f"Identify Client {client_number}",
            f"Which character is logged into Client {client_number}?\n"
            f"Enter the character name:"
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

        identified_count = len(self.client_names)

        self.status_label.setText("Identification Complete")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: green;"
        )

        QMessageBox.information(
            self,
            "Identification Complete",
            f"Client identification finished.\n\n"
            f"Saved character assignments: {identified_count}"
        )

    # ======================================
    # MONITORING CONTROLS
    # ======================================

    def start_monitoring(self):

        client = self.client_combo.currentText()
        handle = self.client_combo.currentData()

        if handle is None:
            QMessageBox.warning(
                self,
                "Missing Client",
                "Please select a game client."
            )
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
                "Please enter at least one character name."
            )
            return

        if not self.killed_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Missing Alert",
                "Please select at least one alert type."
            )
            return

        badges = [
            checkbox.isChecked()
            for checkbox in [
                self.sys_checkbox,
                self.talk_checkbox,
                self.wrld_checkbox,
                self.no_badge_checkbox,
            ]
        ]

        if not any(badges):
            QMessageBox.warning(
                self,
                "Missing Badge",
                "Please select at least one badge filter."
            )
            return

        self.is_monitoring = True
        self.is_paused = False

        self.status_label.setText("Monitoring")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: green;"
        )

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        self.pause_button.setText("Pause")

        print("Monitoring started!")
        print("Client:", client)
        print("Window handle:", handle)
        print("Characters:", characters)

    def pause_monitoring(self):

        if not self.is_monitoring:
            return

        self.is_paused = not self.is_paused

        if self.is_paused:

            self.status_label.setText("Paused")
            self.status_label.setStyleSheet(
                "font-weight: bold; color: orange;"
            )

            self.pause_button.setText("Resume")

        else:

            self.status_label.setText("Monitoring")
            self.status_label.setStyleSheet(
                "font-weight: bold; color: green;"
            )

            self.pause_button.setText("Pause")

    def stop_monitoring(self):

        self.is_monitoring = False
        self.is_paused = False

        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: red;"
        )

        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.pause_button.setText("Pause")

        print("Monitoring stopped!")


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ACMonitor()
    window.show()

    sys.exit(app.exec())
