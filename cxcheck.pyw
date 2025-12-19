import sys
import os
import re
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QProgressBar, QScrollArea, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# Constants
SYNC_THRESHOLD = 60

# ---------------------------------------------------------
# DEVICE DETECTION
# ---------------------------------------------------------
def detect_cxadc_devices(max_devices=8):
    detected = []
    
    for dev in range(max_devices):
        device_path = f'\\\\.\\cxadc{dev}'
        
        test_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-f', 'rawvideo',
            '-pixel_format', 'gray8',
            '-video_size', '16x16',
            '-i', device_path,
            '-t', '0.1',
            '-f', 'null', '-'
        ]

        try:
            # CREATE_NO_WINDOW is crucial for .pyw to ensure ffmpeg doesn't popup
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            proc = subprocess.Popen(
                test_cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                creationflags=creation_flags
            )

            stderr = proc.stderr.read().lower()
            
            if "no such file" not in stderr:
                detected.append(dev)
        except:
            pass

    return detected

# ---------------------------------------------------------
# WORKER THREAD
# ---------------------------------------------------------
class DeviceMonitorWorker(QThread):
    stats_update = pyqtSignal(int, float, bool)
    
    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id
        self.is_running = True
        self.process = None

    def run(self):
        pattern = re.compile(r'lavfi\.signalstats\.YMIN=([0-9\.]+)')
        device_path = f'\\\\.\\cxadc{self.device_id}'

        ffmpeg_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-f', 'rawvideo',
            '-pixel_format', 'gray8',
            '-video_size', '1832x625',
            '-i', device_path,
            '-vf', 'scale=1135x625,eq=gamma=0.5:contrast=1.5,signalstats,metadata=mode=print',
            '-f', 'null',
            '-'
        ]

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1, 
                creationflags=creation_flags
            )

            for line in self.process.stderr:
                if not self.is_running:
                    break

                if "lavfi.signalstats.YMIN" not in line:
                    continue

                match = pattern.search(line)
                if match:
                    try:
                        ymin = float(match.group(1))
                        has_signal = ymin < SYNC_THRESHOLD
                        self.stats_update.emit(self.device_id, ymin, has_signal)
                    except ValueError:
                        pass
        except Exception:
            pass # Fail silently in GUI mode or emit error signal if desired
        finally:
            self.stop_process()

    def stop_process(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None

    def stop(self):
        self.is_running = False
        self.stop_process()
        self.quit()
        self.wait()

# ---------------------------------------------------------
# GUI WIDGET ROW
# ---------------------------------------------------------
class DeviceRow(QWidget):
    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        self.lbl_name = QLabel(f"cxadc{self.device_id}")
        self.lbl_name.setFixedWidth(60)
        self.lbl_name.setStyleSheet("font-weight: bold;")

        self.lbl_status = QLabel("WAITING...")
        self.lbl_status.setFixedWidth(100)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("background-color: gray; color: white; border-radius: 4px;")

        self.lbl_value = QLabel("YMIN: --")
        self.lbl_value.setFixedWidth(80)

        self.progress = QProgressBar()
        self.progress.setRange(0, 255)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #3b8eea; }")

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.progress)

        self.setLayout(layout)

    def update_data(self, ymin, has_signal):
        self.lbl_value.setText(f"YMIN: {int(ymin)}")
        
        # Invert logic: Lower YMIN = Stronger Signal
        bar_val = max(0, 255 - int(ymin))
        self.progress.setValue(bar_val)

        if has_signal:
            self.lbl_status.setText("● SIGNAL")
            self.lbl_status.setStyleSheet("background-color: #2e7d32; color: white; border-radius: 4px; font-weight: bold;") 
        else:
            self.lbl_status.setText("○ NO SIGNAL")
            self.lbl_status.setStyleSheet("background-color: #c62828; color: white; border-radius: 4px;") 

# ---------------------------------------------------------
# MAIN WINDOW
# ---------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CXADC Signal Monitor")
        self.resize(600, 400)
        
        self.workers = []
        self.device_rows = {}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        
        header = QLabel("Monitoring Devices")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.main_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.container)
        
        self.main_layout.addWidget(scroll)

        # Use a timer to delay loading slightly so UI appears first
        # or just load immediately
        self.init_devices()

    def init_devices(self):
        devices = detect_cxadc_devices()

        if not devices:
            lbl = QLabel("No cxadc devices found.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.container_layout.addWidget(lbl)
            return

        for dev_id in devices:
            row_widget = DeviceRow(dev_id)
            self.container_layout.addWidget(row_widget)
            self.device_rows[dev_id] = row_widget

            worker = DeviceMonitorWorker(dev_id)
            worker.stats_update.connect(self.handle_update)
            worker.start()
            self.workers.append(worker)

    def handle_update(self, dev_id, ymin, has_signal):
        if dev_id in self.device_rows:
            self.device_rows[dev_id].update_data(ymin, has_signal)

    def closeEvent(self, event):
        for worker in self.workers:
            worker.stop()
        event.accept()

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        # Since .pyw has no console, we must show errors in a message box
        # otherwise the app will just silently fail to open.
        error_app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Fatal Error", f"An error occurred:\n{str(e)}")
        sys.exit(1)