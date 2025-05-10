# cxgui
a gui to capture raw files from cxadc-win-tool for use with vhs-decode

| Features         | Description                          |
|------------------|--------------------------------------|
| Capture          | Captures a .u8 file from cxadc0 |
| Capture Timeout  | How long it will capture the tape
| Saves config.txt | Saves cxvalues to config.txt in the same folder as capture file  |
| dshow Player     | Plays local dshow device like Elgato Game Capture etc |
| rtsp Player      | Plays a network rtsp source like from a go2rtc server |
| VHS Control      | Lets you control a VHS Player by using a Arduino with IR or another service like home assistant if you haved it set up as endpoints |
| Capture Device (TODO) | select the cx capture device

# Install

* working cxadc driver setup on windows (disabled secure boot, disabled enforced driver signing)
* cxadc-win-tool.exe in same folder as cxgui
* pip3 install python-vlc requests
