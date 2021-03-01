#!/bin/bash
NAME="qoemu_Pixel4_API_30_x86"


# get list of currently available avds
avdmanager list avd


avdmanager delete -n $NAME