# QoEmu V0.1

## Installation
When cloning the git repository, check that git lfs is enabled
by using the command ``git lfs install`` and ``git lfs fetch``

## Hardware Device Control
For controlling a real Android phone:
* The phone must be connected to the qoemu host by an USB connection (used for
  UI control and screen capturing)
* USB debugging mode must be enabled on the phone
* The qoemu host must be configured to act as a wireless hotspot for the phone.
* For audio capturing, the phone must be connected via line-out or Bluetooth
  to the qoemu host

### Routing WLAN Traffic of Real Device via QoEmu
In order to enable QoEmu to emulate various networking conditions,
we must route all data traffic of the real mobile device via QoEmu. Therefore,
we enable the QoEmu host to act as a WLAN accesspoint and connect the
mobile device to it. In this way, all traffic of the mobile device
is routed via QoEmu and networking conditions can be emulated in the same 
way as it is done for an emulated device.

For setting up the QoEmu host as a wireless hotspot, two options are available:

1) Ubuntu Network Manager: Wireless Hotspot (simple) 
2) HostAP driver (more complex, various options)

*Using the Ubuntu Network Manager to set up a Hotspot:*

Within the networking menu, "Enable wireless hotspot" can be selected for any
supported WLAN card. (Note: Currently, there seems to be a bug in the
user interface: if the option is greyed-out, simple click on "Networking" on the
right and back on WLAN, then it will be enabled.)


*Command line tools to edit and start the Hotspot:*

``nm-connection-editor`` can be used to edit the settings, e.g. set the
frequency and channel
``nmcli connection up Hotspot`` can be used to enable the hotspot ("Hotspot" is
the default connection name, can also be different - check in connection editor)


*WLAN Hardware and Configuration*:

QoEmu has been tested with
* Driver: [rtl88x2bu](https://github.com/cilynx/rtl88x2bu)
* Disablee Powersaving in Ubuntu 20: Edit ``/etc/NetworkManager/conf.d/default-wifi-powersave-on.conf`` and set

  ```
  [connection]
  wifi.powersave = 2
  ```
  See https://gist.github.com/jcberthon/ea8cfe278998968ba7c5a95344bc8b55 for an
  explanation of the possible values.



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
