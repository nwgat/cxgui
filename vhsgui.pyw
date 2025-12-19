import sys
import os
import shutil
import json
import traceback
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QTextEdit, QCheckBox, QSpinBox, QComboBox, 
                             QGroupBox, QMessageBox)
from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtGui import QTextCursor

CONFIG_FILE = "vhsgui.json"

# --- 1. Crash Handler ---
def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    if QApplication.instance():
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred:\n\n{error_msg}")
    else:
        with open("crash_log.txt", "w") as f:
            f.write(error_msg)
    sys.exit(1)

sys.excepthook = exception_hook

# --- 2. Configuration Manager ---
class ConfigManager:
    @staticmethod
    def load_config():
        defaults = {
            "decode_path": "",
            "tbc_export_path": "",
            "last_input_file": "",
            "window_width": 900,
            "window_height": 750
        }
        if not os.path.exists(CONFIG_FILE):
            return defaults
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # Ensure all keys exist (merging defaults)
                for key in defaults:
                    if key not in data:
                        data[key] = defaults[key]
                return data
        except (json.JSONDecodeError, IOError):
            return defaults

    @staticmethod
    def save_config(config_data):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
        except IOError:
            pass 

class VHSGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VHSGui")
        
        # Load Config
        self.config = ConfigManager.load_config()

        # Apply Saved Window Size
        w = self.config.get("window_width", 900)
        h = self.config.get("window_height", 750)
        self.resize(w, h)
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.finished.connect(self.process_finished)
        
        self.current_step = None 
        self.work_dir = "" 

        self.init_ui()
        self.auto_locate_executables()

    def closeEvent(self, event):
        """Handle window closing event to save state."""
        self.config["window_width"] = self.width()
        self.config["window_height"] = self.height()
        ConfigManager.save_config(self.config)
        event.accept()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # --- Config Section ---
        exe_group = QGroupBox("Executable Configuration")
        exe_layout = QVBoxLayout()

        # Decode Row
        row_decode = QHBoxLayout()
        self.path_decode = QLineEdit()
        self.path_decode.setPlaceholderText("Path to decode.exe...")
        self.path_decode.setText(self.config["decode_path"])
        btn_browse_decode = QPushButton("Browse")
        btn_browse_decode.clicked.connect(lambda: self.browse_exe(self.path_decode))
        row_decode.addWidget(QLabel("Decode.exe:"))
        row_decode.addWidget(self.path_decode)
        row_decode.addWidget(btn_browse_decode)
        exe_layout.addLayout(row_decode)

        # Export Row
        row_export = QHBoxLayout()
        self.path_export = QLineEdit()
        self.path_export.setPlaceholderText("Path to tbc-video-export.exe...")
        self.path_export.setText(self.config["tbc_export_path"])
        btn_browse_export = QPushButton("Browse")
        btn_browse_export.clicked.connect(lambda: self.browse_exe(self.path_export))
        row_export.addWidget(QLabel("Export.exe:"))
        row_export.addWidget(self.path_export)
        row_export.addWidget(btn_browse_export)
        exe_layout.addLayout(row_export)

        exe_group.setLayout(exe_layout)
        main_layout.addWidget(exe_group)

        # --- Settings Section ---
        settings_group = QGroupBox("Decode Settings")
        settings_layout = QVBoxLayout()
        
        # Input File
        row_input = QHBoxLayout()
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText("Select Input RF File (.u8, .ldf, .cx, .r8)")
        
        btn_browse_input = QPushButton("Browse...")
        btn_browse_input.clicked.connect(self.browse_input_file)
        row_input.addWidget(QLabel("Input File:"))
        row_input.addWidget(self.input_file)
        row_input.addWidget(btn_browse_input)
        settings_layout.addLayout(row_input)

        # Output Name
        row_output = QHBoxLayout()
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("Output filename (no extension)")
        row_output.addWidget(QLabel("Output Base Name:"))
        row_output.addWidget(self.output_name)
        settings_layout.addLayout(row_output)

        # Args Row 1
        row_args = QHBoxLayout()
        self.combo_format = QComboBox()
        self.combo_format.addItems(["vhs", "svhs", "umatic", "betamax"])
        row_args.addWidget(QLabel("Format:"))
        row_args.addWidget(self.combo_format)

        self.combo_system = QComboBox()
        self.combo_system.addItems(["pal", "ntsc", "mesecam"])
        row_args.addWidget(QLabel("System:"))
        row_args.addWidget(self.combo_system)

        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 64)
        self.spin_threads.setValue(8)
        row_args.addWidget(QLabel("Threads:"))
        row_args.addWidget(self.spin_threads)
        
        settings_layout.addLayout(row_args)

        # Args Row 2 (Frequency & Checkboxes)
        row_args2 = QHBoxLayout()
        
        # Frequency Dropdown
        self.combo_freq = QComboBox()
        self.combo_freq.addItems(["Auto", "28 MHz", "40 MHz"])
        self.combo_freq.setToolTip("Select sampling frequency (Auto uses file header)")
        
        row_args2.addWidget(QLabel("Frequency:"))
        row_args2.addWidget(self.combo_freq)

        # Checkboxes
        self.check_recheck = QCheckBox("--recheck_phase")
        self.check_recheck.setChecked(True)
        row_args2.addWidget(self.check_recheck)
        
        row_args2.addStretch()

        settings_layout.addLayout(row_args2)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("START Workflow")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("font-weight: bold; background-color: #28a745; color: white;")
        self.btn_run.clicked.connect(self.start_process)
        
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setStyleSheet("font-weight: bold; background-color: #dc3545; color: white;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.kill_process)

        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_stop)
        main_layout.addLayout(btn_layout)

        # --- Logs ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 10pt;")
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        main_layout.addWidget(QLabel("Process Log:"))
        main_layout.addWidget(self.log_output)

        self.setLayout(main_layout)

        # --- PRE-FILL DATA ---
        if self.config["last_input_file"] and os.path.exists(self.config["last_input_file"]):
            self.input_file.setText(self.config["last_input_file"])
            self.update_output_name(self.config["last_input_file"])

    def auto_locate_executables(self):
        if not self.path_decode.text():
            found = self.find_executable("decode.exe")
            if found: self.path_decode.setText(found)
        if not self.path_export.text():
            found = self.find_executable("tbc-video-export.exe")
            if found: self.path_export.setText(found)

    def find_executable(self, name):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, name)
        if os.path.exists(local_path):
            return local_path
        return shutil.which(name)

    def browse_exe(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Executable", "", "Executables (*.exe);;All Files (*)")
        if fname:
            line_edit.setText(os.path.normpath(fname))

    def browse_input_file(self):
        # Default start directory is empty (let OS decide)
        start_dir = ""
        
        # If we have a saved file path, extract its folder
        last_file = self.config.get("last_input_file", "")
        if last_file and os.path.exists(last_file):
            start_dir = os.path.dirname(last_file)
        elif last_file:
            # Handle case where file was deleted but we have the string
            possible_dir = os.path.dirname(last_file)
            if os.path.exists(possible_dir):
                start_dir = possible_dir

        fname, _ = QFileDialog.getOpenFileName(
            self, 
            "Select RF Capture", 
            start_dir,  # Open in the remembered folder
            "RF Files (*.u8 *.ldf *.cx *.r8 *.flac);;All Files (*)"
        )
        
        if fname:
            norm_path = os.path.normpath(fname)
            self.input_file.setText(norm_path)
            self.update_output_name(norm_path)

    def update_output_name(self, path):
        base = os.path.splitext(os.path.basename(path))[0]
        self.output_name.setText(base)

    def append_log_text(self, text):
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        safe_text = text.replace('\r', '\n')
        cursor.insertText(safe_text)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def start_process(self):
        decode_exe = self.path_decode.text().strip()
        export_exe = self.path_export.text().strip()
        input_full_path = self.input_file.text().strip()
        output_base_name = self.output_name.text().strip()

        if not os.path.exists(decode_exe):
            QMessageBox.critical(self, "Error", f"Decode executable not found:\n{decode_exe}")
            return
        if not os.path.exists(export_exe):
            QMessageBox.critical(self, "Error", f"Export executable not found:\n{export_exe}")
            return
        if not os.path.exists(input_full_path):
            QMessageBox.critical(self, "Error", f"Input file not found:\n{input_full_path}")
            return
        if not output_base_name:
            QMessageBox.warning(self, "Error", "Please specify an output name.")
            return

        self.config["decode_path"] = decode_exe
        self.config["tbc_export_path"] = export_exe
        self.config["last_input_file"] = input_full_path
        # Note: Window size is saved in closeEvent, but we can save paths here too
        ConfigManager.save_config(self.config)

        self.work_dir = os.path.dirname(input_full_path)
        input_filename = os.path.basename(input_full_path)
        output_arg = os.path.join(self.work_dir, output_base_name)

        self.process.setWorkingDirectory(self.work_dir)
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_output.clear()

        self.current_step = "decode"
        args = ["vhs"]
        args.extend(["--tape_format", self.combo_format.currentText()])
        args.extend(["--system", self.combo_system.currentText()])
        args.extend(["--threads", str(self.spin_threads.value())])
        
        # --- FREQUENCY DROPDOWN LOGIC ---
        freq_text = self.combo_freq.currentText()
        if "28" in freq_text:
            args.extend(["--frequency", "28"])
        elif "40" in freq_text:
            args.extend(["--frequency", "40"])
            
        if self.check_recheck.isChecked():
            args.append("--recheck_phase")
        
        args.append(input_filename)
        args.append(output_arg)

        self.append_log_text(f"--- STARTING DECODE ---\nCommand: {os.path.basename(decode_exe)} {' '.join(args)}\n\n")
        self.process.start(decode_exe, args)

    def kill_process(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.append_log_text("\n\n!!! PROCESS STOPPED BY USER !!!\n")

    def handle_output(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf8", errors="replace")
        self.append_log_text(text)

    def process_finished(self):
        self.btn_stop.setEnabled(False)
        if self.process.exitStatus() == QProcess.ExitStatus.CrashExit:
            self.btn_run.setEnabled(True)
            return

        if self.process.exitCode() != 0:
            self.append_log_text(f"\n!!! {self.current_step.upper()} FAILED (Exit Code {self.process.exitCode()}) !!!\n")
            self.btn_run.setEnabled(True)
            return

        if self.current_step == "decode":
            self.append_log_text("\n\n--- DECODE COMPLETE. STARTING EXPORT ---\n")
            self.start_export()
        elif self.current_step == "export":
            output_base_name = self.output_name.text().strip()
            expected_mkv = os.path.join(self.work_dir, f"{output_base_name}.tbcexported.mkv")
            
            if os.path.exists(expected_mkv):
                self.append_log_text("\n\n--- ALL TASKS COMPLETED SUCCESSFULLY ---\n")
                QMessageBox.information(self, "Success", "Workflow Finished!")
            else:
                self.append_log_text(f"\n\n!!! ERROR: Output file not found !!!\nExpected: {expected_mkv}\nCheck log for errors above.")
                QMessageBox.warning(self, "Export Failed", "The process finished, but the output .mkv file is missing.")
            
            self.btn_run.setEnabled(True)
            self.current_step = None

    def start_export(self):
        self.current_step = "export"
        output_base_name = self.output_name.text().strip()
        export_exe = self.path_export.text().strip()
        
        tbc_filename = f"{output_base_name}.tbc"
        export_filename = f"{output_base_name}.tbcexported.mkv"
        
        full_tbc_path = os.path.join(self.work_dir, tbc_filename)
        if not os.path.exists(full_tbc_path):
             self.append_log_text(f"\nError: Could not find generated file: {tbc_filename}\n")
             self.btn_run.setEnabled(True)
             return

        self.process.setWorkingDirectory(self.work_dir)
        args = [tbc_filename, export_filename]
        
        self.btn_stop.setEnabled(True)
        self.append_log_text(f"Command: {os.path.basename(export_exe)} \"{tbc_filename}\" \"{export_filename}\"\n\n")
        
        self.process.start(export_exe, args)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VHSGui()
    window.show()
    sys.exit(app.exec())