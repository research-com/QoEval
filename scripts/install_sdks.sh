#!/bin/bash

if ! hash sdkmanager 2>/dev/null
then
    echo "'sdkmanager' was not found - please install Android Studio and sdk first."
    exit 1
fi

sdkmanager --install "platforms;android-29"
sdkmanager --install "platforms;android-30"
