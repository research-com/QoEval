#!/bin/bash
#
# script to install the dependencies required for QoEmu
#
# Note: A NVIDIA graphics card is required (tested on GTX1060)

# Versions
NDK_VERSION="23.0.7123448"

# configuration settings
SHELL="terminator git git-lfs"
OS_TOOLS="net-tools htop qemu-kvm bridge-utils cpu-checker vlc vlc-plugin-base vlc-plugin-video-output"
MONITORING="wireshark wireshark-qt wireshark-doc"
VIDEO_REC="ffmpeg vlc-bin wmctrl x11-utils gpac"
REMOTE_ACCESS="openssh-server"
JAVA="openjdk-8-jre"
PYTHON="python3-venv python3-pip"
# VULKAN="nvidia-driver-460 nvidia-settings vulkan-utils vulkan-tools"
BROWSER="firefox"
SCRCPY="ffmpeg libsdl2-2.0-0 adb wget gcc git pkg-config meson ninja-build libavcodec-dev libavformat-dev libavutil-dev libsdl2-dev"

USER="qoe-user"
set -o errexit # fail if any command fails


# other constants
SCRIPT_DIR="$(dirname $(readlink -f $0))"
APT="apt-get -y"
# APT="echo"
PATHMOD_ID="# QoE path setup"
SUDOERMOD_ID="# QoE sudo commands"
BASHRC="/home/$USER/.bashrc"
SUDOERS="/etc/sudoers"
ANDROIDSTUDIO_DL="https://developer.android.com/studio"
GENYMOTION_DL="https://www.genymotion.com/"

if [[ $EUID -ne 0 ]]; then
  echo "Only a root user can run this script!" 2>&1
  exit 1
fi

# add PPA for NVIDIA proprietary drivers
# add-apt-repository ppa:oibaf/graphics-drivers

# update and upgrade packages
$APT update
$APT upgrade

# install all dependencies
$APT install $SHELL
$APT install $OS_TOOLS
$APT install $SCRCPY

# $APT install $VULKAN

$APT install $MONITORING
usermod -a -G wireshark $USER
# su -c "newgrp wireshark" $USER

$APT install $VIDEO_REC
$APT install $REMOTE_ACCESS
$APT install $JAVA
$APT install $PYTHON
$APT install $BROWSER

usermod -a -G kvm $USER
# su -c "newgrp kvm" $USER

# Android Studio Path setup
if grep -Fxq "$PATHMOD_ID" $BASHRC
then
   echo "$BASHRC seems to be updated - modification skipped"
else
   echo "Modifying $BASHRC to include the necessary paths..."
   echo "$PATHMOD_ID" >> $BASHRC
   NEWPATH='$PATH':$SCRIPT_DIR:'$HOME/pycharm/bin:$HOME/android-studio/bin:$HOME/Android/Sdk/tools/bin:$HOME/Android/Sdk/platform-tools:$HOME/Android/Sdk/emulator:$HOME/Android/Sdk/ndk/'$NDK_VERSION:'$HOME/genymotion/genymotion'
   echo "export PATH=$NEWPATH" >> $BASHRC
fi

# adding required commands to sudoers file
if grep -Fxq "$SUDOERMOD_ID" $SUDOERS
then
   echo "$SUDOERS seems to be updated - modification skipped"
else
   echo "Modifying $SUDOERS to include the necessary paths..."
   echo "$SUDOERMOD_ID" >> $SUDOERS
   echo "$USER  ALL=(ALL) NOPASSWD: /usr/sbin/tc" >> $SUDOERS
   echo "$USER  ALL=(ALL) NOPASSWD: /usr/sbin/ip" >> $SUDOERS
   echo "$USER  ALL=(ALL) NOPASSWD: /usr/sbin/modprobe" >> $SUDOERS
fi

# Disable assistive_technologies property
sed -i -e '/^assistive_technologies=/s/^/#/' /etc/java-*-openjdk/accessibility.properties

echo ""
echo "Please manually install Android Studio to its default location ('$HOME/android-studio')."
echo "For Python development, we recommend to install PyCharm to $HOME/pycharm."
echo ""
echo "It can be downloaded at $ANDROIDSTUDIO_DL"
echo ""
echo ""
echo "For improved emulation, you can also Genymotion. It can be downloaded at $GENYMOTION_DL"
echo "Genymotion requires a separate, commercial license if not being used for education."
echo
echo "Note: You need to reboot the machine for all group changes to take effect."

