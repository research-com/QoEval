#!/bin/bash
#
# script to install the dependencies required for QoEmu

# configuration settings
SHELL="terminator git git-lfs"
OS_TOOLS="net-tools htop"
MONITORING="wireshark wireshark-qt wireshark-doc"
VIDEO_REC="ffmpeg vlc-bin"
REMOTE_ACCESS="openssh-server"
JAVA="openjdk-8-jre"
BROWSER="firefox"

USER="qoe-user"



# other constants
SCRIPT_DIR="$(dirname $(readlink -f $0))"
APT="apt"
# APT="echo"
PATHMOD_ID="# QoE path setup"
BASHRC="/home/$USER/.bashrc"
ANDROIDSTUDIO_DL="https://developer.android.com/studio"

if [[ $EUID -ne 0 ]]; then
  echo "Only a root user can run this script!" 2>&1
  exit 1
fi

$APT update
$APT install $SHELL
$APT install $OS_TOOLS

$APT install $MONITORING
usermod -a -G wireshark $USER

$APT install $VIDEO_REC
$APT install $REMOTE_ACCESS
$APT install $JAVA
$APT install $BROWSER

usermod -a -G kvm $USER

# Android Studio Path setup
if grep -Fxq "$PATHMOD_ID" $BASHRC
then
   echo "$BASHRC seems to be updated - modification skipped"
else
   echo "Modifying $BASHRC to include the necessary paths..."
   echo "$PATHMOD_ID" >> $BASHRC
   NEWPATH='$PATH':$SCRIPT_DIR:'$HOME/android-studio/bin:$HOME/Android/Sdk/tools/bin'
   echo "export PATH=$NEWPATH" >> $BASHRC
fi

echo ""
echo "Please manually install Android Studio to its default location ('$HOME/android-studio')."
echo ""
echo "Press ENTER to open the download page ($ANDROIDSTUDIO_DL)."
read
su -c "firefox $ANDROIDSTUDIO_DL" $USER
