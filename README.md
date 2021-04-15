# QoEmu V0.1

## Hardware Device Control
For controlling a real Android phone:
* The phone must be connected to the qoemu host by an USB connection (used for
  UI control and screen capturing)
* USB debugging mode must be enabled on the phone
* The qoemu host must be configured to act as a wireless hotspot for the phone.
* For audio capturing, the phone must be connected via line-out or Bluetooth
  to the qoemu host

## Device Emulation

### Genymotion Desktop
For device emulation, the Genymotion (see https://www.genymotion.com/desktop/) is recommended. It requires a license for commercial use as an independent 
developer of within a company, personal use is free of charge.

The emulator has better performance and audio capabilities than the standard
emulator. 

### Standard Emulator (included in Android SKD)
As a fallback solution, the standard [Android emulation that is included
within the Android SDK](https://developer.android.com/studio/run/emulator-commandline) can be used.

However, since in this emulator the bridged networking mode is not available,
network emulation cannot be limited to the IP of the emulator

## Device Control

For controlling the device, [AndroidViewClient](https://github.com/dtmilano/AndroidViewClient) is required. 

Alternatives (currently not used in the project):
* monkeyrunner API via Python: https://developer.android.com/studio/test/monkeyrunner/, https://www.thegeekstuff.com/2014/08/monkeyrunner-android/
* monkey tool via adb: \
  `monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1` 
* `uiautomatorviewer` (sdk tool) to get x,y