# QoEmu V0.1

## Installation

Clone the repository and change to the qoemu directory.

```
git clone --recursive [URL to repo]
cd qoemu
```

### git LFS required
When cloning the git repository, check that git lfs is enabled
by using the command ``git lfs install`` and ``git lfs fetch``

### System setup
We strongly recommend to use a virtual environment
```
python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip3 install -r requirements.txt
```

### Building the package
The python setuptools and a builder (e.g. PyPA build) are used to build the package:
```
pip3 install build
python3.8 -m build
```

Afterwards, the package can be installed using pip:

```
pip3 install dist/qoemu-pkg-hm-0.1.0.tar.gz
```

### Running QoEmu
A user-friendly GUI for QoEmu is currently under development. Until it is available,
the ``coordinator.py`` is used to control the emulation.


### Optional Additional Post-Processing Tools: Lossless Cut
Basic postprocessing is performed by QoEmu using trigger frames to detect
the beginning and the end of a stimuli section. If you want to apply
additional postprocessing, a *lossless* video manipulation tool can 
be used. We recommend https://github.com/mifi/lossless-cut.git

#### Remarks regarding installation of lossless-cut
* For starting lossless-cut, see the developer-notes within the
lossless-cut repo.

* Yarn needs to be installed in a current version:
```
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add - 
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list 
sudo apt update 
sudo apt install yarn
```
* `node` needs to be updated to a recent version, e.g. by using the node version manager (nvm)


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

QoEmu in combination with a real Android phone has mainly been tested with a Realtek based USB3 WLAN adaptor 
(0bda:b812 Realtek Semiconductor Corp. RTL88x2bu [AC1200 Techkey]). Since Ubuntu 20.10, this device is
supported without installing any further drivers manually. However, we recommend the following module options
`rtw_vht_enable=2 rtw_switch_usb_mode=1 rtw_power_mgnt=0`.

### Old WLAN configuration (Ubuntu 20.04 and earlier)
Some WLAN cards such as the 
* Driver: [rtl88x2bu](https://github.com/morrownr/88x2bu)
  settings in ` /etc/modprobe.d/88x2bu.conf `: `options 88x2bu rtw_drv_log_level=0 rtw_led_ctrl=1 rtw_vht_enable=1 rtw_power_mgnt=0 rtw_switch_usb_mode=1`
* Alternative Driver - causes issues with delays exceeding 40ms: [rtl88x2bu](https://github.com/cilynx/rtl88x2bu)
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


## Known Bugs and Problems
The 4.15 Linux kernel as well as the 5.8.0 kernel have a bug within the netem module which 
leads to incorrectly emulated delays. (see https://superuser.com/questions/1338567/jitter-generation-with-netem-is-not-working and
and https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1783822 for more information).

*Recommendation:*

Before generating QoEmu stimuli, confirm (e.g. by a bandwidth measurement app on your mobile/emulated device)
that the measured delays are as expected/configured within QoEmu. If the delays are significantly higher
than expected or vary to an extremely large extend, update your linux kernel and check that the WLAN
device driver is working properly and all power-saving features have been disabled.

