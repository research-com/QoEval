# TODO


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
* alternative: use emulator console to record https://developer.android.com/studio/run/emulator-console

## Screen-Recording of real device
### ADB
https://programmer.group/adb-screen-capture-and-recording-commands.html

### copy to host
adb pull /sdcard/somedir

### Python related
* Xlib to get window dimensions for recording: https://unix.stackexchange.com/questions/5999/setting-the-window-dimensions-of-a-running-application
* Screen recording in Windows: https://github.com/coderman64/screen-recorder


## Audio-Recording of Emulator Window
* get source index: pacmd list-sources     - look for index of monitor
* -i [nr]  or -i [name] in ffmpeg
* see https://trac.ffmpeg.org/wiki/Capture/PulseAudio

### Links / Further Info
* https://pythonprogramming.altervista.org/record-the-screen-with-ffmpeg-and-python/


## Emulator console
* Can be controlled (after auth) via tcp connection: https://developer.android.com/studio/run/emulator-console 

### Add parameter values to meta-data of recorded video

# Misc

## Sound Chip in QoE local i7 server
```
qoe-user@qoemu-01:~$ cat /proc/asound/card
card0/ card1/ cards  
qoe-user@qoemu-01:~$ cat /proc/asound/cards
 0 [PCH            ]: HDA-Intel - HDA Intel PCH
                      HDA Intel PCH at 0xdf240000 irq 136
 1 [NVidia         ]: HDA-Intel - HDA NVidia
                      HDA NVidia at 0xdf080000 irq 17
qoe-user@qoemu-01:~$ head -n 1 /proc/asound/card0/codec*
Codec: Realtek ALC887-VD
qoe-user@qoemu-01:~$ 
```

Added to `/etc/modprobe.de/alsa-base.conf`: 
```
options snd-hda-intel model=generic power_save=0 power_save_controller=N
```

## Native Development Kit - Compiling from Command Line

* https://www.codeproject.com/Articles/1071782/Building-an-Android-Command-Line-Application-Using
