#!/bin/python3
"""
    Emulator control
"""

import logging as log
import os
import subprocess
import shlex

# Define constants
TARGET_NAME = "android-30"
DEVICE_NAME = "pixel"
AVD_NAME = "qoemu_" + DEVICE_NAME + "_" + TARGET_NAME.replace("-","_") + "_x86"

EMU_NAME = "emulator"
AVD_MANAGER_NAME = "avdmanager"
SDK_MANAGER_NAME = "sdkmanager"


def check_env():
    log.info("checking availability of AVD emulator...")
    check_ext(EMU_NAME)
    log.info("checking availability of AVD manager...")
    check_ext(AVD_MANAGER_NAME)
    log.info("checking availability of SDK manager...")
    check_ext(SDK_MANAGER_NAME)


def check_ext(name):
    log.debug(f"locating {name}")
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - please install AndroidStudio.")
        raise RuntimeError('External component not found.')
    else:
        log.debug(f"using {output.stdout}")


def is_avd_available(name):
    log.debug(f"checking if AVD {name} is available")
    output = subprocess.run(shlex.split(f"{AVD_MANAGER_NAME} list avd"), stdout=subprocess.PIPE,
                            universal_newlines=True)
    if output.stdout.find(name) == -1:
        log.info(f"AVD {name} is NOT available.")
        print (output.stdout)
        return False
    else:
        return True


def is_target_available(name):
    log.debug(f"checking if target {name} is available")
    output = subprocess.run(shlex.split(f"{AVD_MANAGER_NAME} list target"), stdout=subprocess.PIPE,
                            universal_newlines=True)
    return output.stdout.find("\"" + name + "\"") != -1


def download_target(name):
    log.debug(f"downloading target {name}")
    output = subprocess.run(shlex.split(f"{SDK_MANAGER_NAME} --install \"platforms;{name}\""), stdout=subprocess.PIPE,
                            universal_newlines=True)


def is_device_available(name):
    log.debug(f"checking if device {name} is available")
    output = subprocess.run(shlex.split(f"{AVD_MANAGER_NAME} list device"), stdout=subprocess.PIPE,
                            universal_newlines=True)
    return output.stdout.find("\"" + name + "\"") != -1


def create_avd(name):
    log.debug(f"Creating AVD {name}")
    # check that the required target and device are available
    if not is_target_available(TARGET_NAME):
        download_target(TARGET_NAME)
        if not is_target_available(TARGET_NAME):
            raise RuntimeError('Downloading the required target failed.')

    output = subprocess.run(shlex.split(
        f"{AVD_MANAGER_NAME} create avd --package 'system-images;{TARGET_NAME};google_apis;x86' --path ./avds " +
        f"--device \"{DEVICE_NAME}\" --name {AVD_NAME}"),
        stdout=subprocess.PIPE,
        universal_newlines=True)
    output.check_returncode()


def delete_avd(name):
    log.debug(f"Deleting AVD {name}")
    output = subprocess.run(shlex.split(
        f"{AVD_MANAGER_NAME} delete avd --name {AVD_NAME}"),
        stdout=subprocess.PIPE,
        universal_newlines=True)


def is_acceleration_available():
    output = subprocess.run(shlex.split(f"{EMU_NAME} -accel-check"), stdout=subprocess.PIPE,
                            universal_newlines=True)
    return output.stdout.find("is installed and usable.") != -1


class Emulator:

    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        check_env()
        self.avd_name = AVD_NAME

    def launch_emulator(self):
        log.info("Launching emulator...")
        delete_avd(self.avd_name)  # enable this line to reset upon each start
        if not is_avd_available(self.avd_name):
            create_avd(self.avd_name)
        if not is_acceleration_available():
            log.warning("Accelerated emulation is NOT available, emulation will be too slow.")
        output = subprocess.run(shlex.split(
            f"{EMU_NAME} -avd {AVD_NAME} -accel auto -gpu host "),
            stdout=subprocess.PIPE,
            universal_newlines=True)


if __name__ == '__main__':
    # executed directly as a script
    print("Emulator control")
    emu = Emulator()
    emu.launch_emulator()
