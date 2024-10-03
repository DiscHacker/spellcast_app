import win32gui, time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QMessageBox, QLineEdit, QCheckBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import pygetwindow as gw
from PIL import Image
from src.autoscan import AutoScan

class CaptureThread(QThread):
    # Define signals to send the results and timing back to the main thread
    result_ready = pyqtSignal(list, list, list, Image.Image)
    error_occurred = pyqtSignal(int)
    
    def __init__(self, window_name, swap, scan, parent=None):
        super(CaptureThread, self).__init__(parent)
        self.window_name = window_name
        self.swap = swap
        self.scan = scan
    
    def run(self):
        start = time.time()
        try: 
            hwnd = win32gui.FindWindow(None, self.window_name)
            game_screen = self.scan.get_image(hwnd)
        except: return self.error_occurred.emit(0)

        try: board = self.scan.get_board(game_screen)
        except: return self.error_occurred.emit(1)

        batch, checks = self.scan.get_cells(board)
        chars = self.scan.get_chars(batch)
        ocrtime = round(time.time() - start, 2)
        results = self.scan.run(checks, chars, self.swap)
        solvetime = round(time.time() - start - ocrtime, 2)
        
        timedata = [ocrtime, solvetime, round(ocrtime + solvetime, 2)]
        data = []
        coord_data = []
        
        for i, node in enumerate(results):
            word, score, gem, coordinates, swap_strings = node.to_string(self.scan.game)
            data.append(f"{i + 1} > {word} - {score} points - {gem} gems")
            coord_data.append([coordinates, swap_strings])
        
        return self.result_ready.emit(data, timedata, coord_data, board)


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.board = None
        self.coord_data = None
        self.capturing = False
        self.scan = AutoScan()

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_button_text)
        self.capture_text = "Capturing"
        self.animation_step = 0

        self.capture_thread = None  # Thread for running the capture process

    def initUI(self):
        self.setWindowTitle('Window Capture App')
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        main_layout = QHBoxLayout()

        # Left section
        left_layout = QVBoxLayout()

        self.left_dropdown = QComboBox()
        self.left_dropdown.currentIndexChanged.connect(self.solution_select)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.left_dropdown)
        left_layout.addWidget(self.image_label)

        # Right section
        right_layout = QVBoxLayout()
        self.pin_button = QPushButton('PIN')
        self.pin_button.setCheckable(True)  # Allow it to be toggled
        self.pin_button.clicked.connect(self.toggle_pin)

        self.window_dropdown = QComboBox()
        self.window_dropdown.addItems([w.title for w in gw.getAllWindows() if w.title ])
        self.window_dropdown.setFixedWidth(230)

        # Autotrack label, checkbox, and input
        self.autotrack_checkbox = QCheckBox()  # Checkbox for Autotrack feature
        self.autotrack_checkbox.setChecked(True)
        self.autotrack_label = QLabel("AUTOTRACK WINDOW")
        
        self.autotrack_input = QLineEdit()  # Add the Autotrack input
        self.autotrack_input.setText("Discord")
        self.autotrack_input.setPlaceholderText("Enter autotrack text")  # Set placeholder text
        self.autotrack_input.setFixedWidth(230)

        # Adding checkbox and label to a horizontal layout
        autotrack_layout = QHBoxLayout()
        autotrack_layout.addWidget(self.autotrack_checkbox)
        autotrack_layout.addWidget(self.autotrack_label)
        autotrack_layout.setContentsMargins(0, 0, 0, 0)

        self.refresh_button = QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh_button.setFixedWidth(230)

        self.option_dropdown = QComboBox()
        self.option_dropdown.addItems(['0', '1', '2'])
        self.option_dropdown.setFixedWidth(230)

        self.capture_button = QPushButton('Capture')
        self.capture_button.clicked.connect(self.start_capture)
        self.capture_button.setFixedWidth(230)

        # New labels for time data
        self.total_time_label = QLabel('OCR Time: N/A')
        self.total_time_label.setFixedWidth(230)
        self.ocr_time_label = QLabel('Solving Time: N/A')
        self.ocr_time_label.setFixedWidth(230)
        self.solving_time_label = QLabel('Total Time: N/A')
        self.solving_time_label.setFixedWidth(230)

        right_layout.addWidget(self.pin_button)
        right_layout.addWidget(self.window_dropdown)
        right_layout.addWidget(self.refresh_button)
        right_layout.addLayout(autotrack_layout)  # Add the autotrack layout
        right_layout.addWidget(self.autotrack_input)  # Add the Autotrack input to layout
        right_layout.addWidget(self.option_dropdown)
        right_layout.addWidget(self.capture_button)
        right_layout.addWidget(self.total_time_label)
        right_layout.addWidget(self.ocr_time_label)
        right_layout.addWidget(self.solving_time_label)
        right_layout.setAlignment(Qt.AlignTop)

        # Add layouts to main layout
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

        self.setLayout(main_layout)

    def toggle_pin(self):
        # Toggle the always on top state
        if self.pin_button.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_button.setText('UNPIN')
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_button.setText('PIN')
        self.show()  # Update the window to reflect changes

    def show_error(self, error):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText("An error occurred")
        msg_box.setInformativeText(error) 
        msg_box.setWindowTitle("Error")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def refresh(self):
        self.window_dropdown.clear()
        self.window_dropdown.addItems([w.title for w in gw.getAllWindows() if w.title])

    def start_capture(self):
        if self.capturing: return
        else: self.capturing = True

        if self.autotrack_checkbox.isChecked():
            autotrack_text = self.autotrack_input.text().strip()
            self.refresh()
            matching_index = -1
            for index in range(self.window_dropdown.count()):
                if autotrack_text in self.window_dropdown.itemText(index):
                    matching_index = index
                    break
            
            if matching_index != -1:
                self.window_dropdown.setCurrentIndex(matching_index)  # Select the matching option
            else:
                self.on_error_occurred(0)

        selected_window = self.window_dropdown.currentText()
        selected_swap = int(self.option_dropdown.currentText())

        # Start the button text animation
        self.animation_step = 1
        self.animation_timer.start(500)

        # Create and start a thread for the capture process
        self.capture_thread = CaptureThread(selected_window, selected_swap, self.scan)
        self.capture_thread.result_ready.connect(self.on_capture_complete)
        self.capture_thread.error_occurred.connect(self.on_error_occurred)
        self.capture_thread.start()

    def on_error_occurred(self, code):
        self.capturing = False
        self.animation_timer.stop()
        self.capture_button.setText("Capture")
        if code == 0:
            self.show_error("Window not found")
        elif code == 1:
            self.show_error("No board found in this window")

    def on_capture_complete(self, data, time_data, coord_data, board):
        self.capturing = False
        # Stop the button text animation and reset the button text
        self.animation_timer.stop()
        self.capture_button.setText("Capture")

        self.coord_data = coord_data
        self.board = board

        self.left_dropdown.clear()
        self.left_dropdown.addItems(data)

        # Update time labels
        self.total_time_label.setText(f"OCR Time: {time_data[0]}s")
        self.ocr_time_label.setText(f"Solving Time: {time_data[1]}s")
        self.solving_time_label.setText(f"Total Time: {time_data[2]}s")

    def solution_select(self):
        i = self.left_dropdown.currentIndex()
        coordinates, swapstrings = self.coord_data[i]
        image = self.scan.coordinator(self.board, coordinates, swapstrings)
        data = image.convert("RGBA").tobytes("raw", "RGBA")
        qimage = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_button_text(self):
        # Cycle through "Capturing", "Capture .", "Capture ..", "Capture ..."
        dots = '.' * (self.animation_step % 5)
        self.capture_button.setText(f"{self.capture_text}{dots}")
        self.animation_step += 1