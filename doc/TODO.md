# TODO

## Python script to read parameters and control netem
* netem tools
* needs to be synchronized with device control
* add dynamic delay
* realize t_init via iptables?


## Python and Control Device
* monkeyrunner API via Python: https://developer.android.com/studio/test/monkeyrunner/
  * https://www.thegeekstuff.com/2014/08/monkeyrunner-android/
* monkey tool via adb: monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1 
* uiautomatorviewer (sdk tool) to get x,y

### Script using avdmanager to create suitable virtual device
* check if suitable device is available, create it if not available
* see https://developer.android.com/studio/command-line/avdmanager

### Start Emulator
* see https://developer.android.com/studio/run/emulator-commandline
* example: emulator -avd Pixel_3a_API_30_x86

### Further Info
* [List of Commands via ADB](https://riptutorial.com/android/example/3958/send-text--key-pressed-and-touch-events-to-android-device-via-adb)
* [input and sendevent/getevent](https://stackoverflow.com/questions/4386449/send-touch-events-to-a-device-via-adb)

## Screen-Recording of Emulator Window
* Window can be identified by window title
* tool: ffpeg
  * example: ffmpeg -video_size 1024x768 -framerate 25 -f x11grab -i :1+100,200 output.mp4 
    * tool to select and show window coordinates: slop
    * window id: wndctrl -l
    * ffmpeg documentaion: https://ffmpeg.org/documentation.html
    * ffmpeg x11 device documentation: https://ffmpeg.org/ffmpeg-devices.html#x11grab
* alternative tool: gstreamer
  * examples:
    * gst-launch-1.0 ximagesrc xid=0x03c00005 ! video/x-raw,framerate=5/1 ! videoconvert ! theoraenc ! oggmux ! filesink location=desktop.ogg
    * gst-launch-1.0 ximagesrc xid=0x03c00005 ! video/x-raw,framerate=5/1 ! videoconvert ! queue ! x264enc pass=5 quantizer=26 speed-preset=6 ! mp4mux fragment-duration=500 ! filesink location="capture.mp4" 
    * gst-launch-1.0 ximagesrc xid=0x03c00005 ! videoconvert ! autovideosink
  * help: You can see the options supported by GStreamer elements using the gst-inspect-1.0 program, e.g.:
    `gst-inspect-1.0 ximagesrc`

### Python related
* Xlib to get window dimensions for recording: https://unix.stackexchange.com/questions/5999/setting-the-window-dimensions-of-a-running-application


## Audio-Recording of Emulator Window
* get source index: pacmd list-sources     - look for index of monitor
* -i [nr] in ffmpeg

### Links / Further Info
* https://pythonprogramming.altervista.org/record-the-screen-with-ffmpeg-and-python/


### Add parameter values to meta-data of recorded video

# Misc

## Native Development Kit - Compiling from Command Line

* https://www.codeproject.com/Articles/1071782/Building-an-Android-Command-Line-Application-Using
