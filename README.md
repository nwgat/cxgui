# CXADC Capture & Preview GUI

A robust, cross-platform (Windows & Linux) GUI application for controlling **CXADC** raw RF capture devices. This tool integrates raw data dumping with real-time video monitoring via **FFmpeg** and **Libmpv**, wrapped in a modern dark-themed interface.

It is designed to run silently as a windowed application (`.pyw`) without persistent console windows, making it ideal for dedicated capture stations.

## Features

* **Raw RF Capture:** Direct binary dumping from CXADC devices (`/dev/cxadc0` or `\\.\cxadc0`) with configurable timeouts.
* **Real-time Preview:** Uses FFmpeg to stream the capture card's video/audio to a local UDP stream, playable inside the GUI via Libmpv.
* **Simultaneous Recording:**
    * Dump raw RF (for software decoding/VHS-decode).
    * Record conventional Video+Audio (`.mkv`) from the preview stream.
    * Record Audio-only from preview stream (`.flac`) for high quality audio capture.
* **Cross-Platform:** Works on Windows (DirectShow + WMI) and Linux (V4L2 + ALSA + Sysfs).
* **Device Management:** Auto-detects video/audio devices and specific CXADC hardware paths.
* **Crash Safety:** Includes custom exception hooks and logging to catch errors even when running in "No Console" mode.

## Prerequisites

### 1. Python Libraries
* Install the required dependencies:
* pip install PyQt6 python-mpv wmi requests
(Note: wmi is only required on Windows)

### 2. External Tools
FFmpeg: Must be installed and added to your system PATH.
* Windows: Download from gyan.dev, extract, and add the bin folder to Environment Variables.
* Linux: sudo apt install ffmpeg

Libmpv:
* Windows: You need the mpv-1.dll (or libmpv-2.dll). Place it in the same folder as this script.
* Linux: sudo apt install libmpv-dev mpv

## Installation
* Clone this repository.
* Ensure you have the CXADC drivers installed for your specific OS.
* Place mpv-1.dll in the script directory (Windows only).
* Run the script.

## Usage
* Running the Application
* To run without a console window (Windowed Mode):
* Rename the script to .pyw extension (e.g., cxadc_gui.pyw).
* Double-click the file.

To run with a console (for debugging):
* `python cxadc_gui.py`

## Workflow
* Left Panel (Device Control):
* Select your CXADC device.
* Set the output path for the raw RF dump (.u8 file).
* Set the capture timeout.
* Check Start preview if you want to see the video while capturing.
* Click Start CX Capture Sequence.

Right Panel (Monitor):
* Select the conventional Video/Audio source (e.g., the composite video input of the card).
* This is used for the "Preview" stream.
* You can change Aspect Ratio or Codec settings here.

Configuration
* The app automatically saves your settings to config.json in the application directory upon closing.
* Crash Logs: If the application fails to start or crashes silently, check crash_log.txt in the script folder.
* Application Logs: General runtime info is saved to cxgui.log.

## Troubleshooting
* "MPV library not found"
Windows: Ensure mpv-1.dll is in the same folder as the script. You may need to add the folder to your user PATH variable or install the mpv python package carefully.
Linux: Ensure libmpv.so is available (sudo apt install libmpv1).

* "Permission Denied" on Linux
Accessing /dev/cxadc0 requires root privileges or adding your user to the video group.
Try: sudo usermod -a -G video $USER (requires logout/login).
