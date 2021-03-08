#!/usr/bin/env python3
"""
    Emulator control
"""
import configparser
import logging as log
import subprocess
import shlex
import os
from enum import Enum
from qoemu_pkg.configuration import avd_path

# Define constants
TARGET_NAME = "android-30"
DEVICE_NAME = "pixel"
AVD_NAME = "qoemu_" + DEVICE_NAME + "_" + TARGET_NAME.replace("-", "_") + "_x86"

EMU_NAME = "emulator"
AVD_MANAGER_NAME = "avdmanager"
SDK_MANAGER_NAME = "sdkmanager"

AVD_INI_FILE = f"{avd_path}/config.ini"


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
        print(output.stdout)
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


def is_acceleration_available():
    output = subprocess.run(shlex.split(f"{EMU_NAME} -accel-check"), stdout=subprocess.PIPE,
                            universal_newlines=True)
    return output.stdout.find("is installed and usable.") != -1


def is_avd_config_readable() -> bool:
    if os.access(f"{AVD_INI_FILE}", os.R_OK):
        return True
    else:
        return False


class EmulatorOrientation(Enum):
    PORTRAIT = 'portrait'
    LANDSCAPE = 'landscape'


class Emulator:

    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        check_env()
        self.avd_name = AVD_NAME
        self.config = None

    def create_avd(self, playstore=False):
        log.debug(f"Creating AVD {self.avd_name}")
        # check that the required target and device are available
        if not is_target_available(TARGET_NAME):
            download_target(TARGET_NAME)
            if not is_target_available(TARGET_NAME):
                raise RuntimeError('Downloading the required target failed.')
        # use avdmanager to create AVD
        # note: in order to be able to enable playstore, package must include "google_apis_playstore"
        if playstore:
            package= f'system-images;{TARGET_NAME};google_apis_playstore;x86'
        else:
            package = f'system-images;{TARGET_NAME};google_apis;x86'

        output = subprocess.run(shlex.split(
            f"{AVD_MANAGER_NAME} create avd --package {package} --path {avd_path} " +
            f"--device \"{DEVICE_NAME}\" --name {self.avd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()
        self.set_standard_parameters()

    def delete_avd(self):
        log.debug(f"Deleting AVD {self.avd_name}")
        output = subprocess.run(shlex.split(
            f"{AVD_MANAGER_NAME} delete avd --name {self.avd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def write_avd_config(self):
        log.debug("Writing updated AVD config file")
        new_config = configparser.ConfigParser()
        new_config.optionxform = str
        new_config['config.ini'] = self.config
        # write new config - but remove section header
        config_without_section = '\n'.join(['='.join(item) for item in new_config.items('config.ini')])
        with open(f"{AVD_INI_FILE}", 'w') as f:
            f.write(config_without_section)

    def read_avd_config(self):
        # note: in order to be able to read the avds config.ini file with configparser
        # we must insert a dummy section
        log.debug("Parsing AVD config file")
        with open(f"{AVD_INI_FILE}", 'r') as f:
            config_string = '[config.ini]\n' + f.read()
        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # default would be to change all options to lowercase
        self.config.read_string(config_string)
        self.config = self.config['config.ini']

    def is_playstore_enabled(self) -> bool:
        if not self.config:
            self.read_avd_config()
        if self.config.get('PlayStore.enabled', 'no') == 'yes':
            return True
        else:
            return False

    def set_playstore_enabled(self, is_enabled: bool):
        if not self.config:
            self.read_avd_config()
        if is_enabled:
            new_value = 'yes'
        else:
            new_value = 'no'
        self.config['PlayStore.enabled'] = new_value
        self.write_avd_config()

    def set_standard_parameters(self):
        if not self.config:
            self.read_avd_config()
        self.config['hw.lcd.density'] = '480'
        self.config['hw.keyboard'] = 'yes'
        self.write_avd_config()

    def get_orientation(self):
        if not self.config:
            self.read_avd_config()
        if self.config.get('hw.initialOrientation', 'portrait') == 'landscape':
            return EmulatorOrientation.LANDSCAPE
        else:
            return EmulatorOrientation.PORTRAIT


    def set_orientation(self, orientation: EmulatorOrientation):
        if not self.config:
            self.read_avd_config()
        self.config['hw.initialOrientation'] = orientation.value
        self.config['skin.dynamic'] = 'yes'
        show_skin=False
        if show_skin:
            self.config['showDeviceFrame'] = 'yes'
            self.config['skin.name'] = 'pixel_silver'
            self.config['skin.path'] = '/home/qoe-user/Android/Sdk/skins/pixel_silver'   # FIXME: abs path
            self.config['skin.path.backup'] = '_no_skin'
        else:
            self.config['showDeviceFrame'] = 'no'
            self.config['skin.name'] = '1920x1080'
            self.config['skin.path'] = '_no_skin'
            self.config['skin.path.backup'] = '_no_skin'
        self.write_avd_config()

    def launch_emulator(self, orientation=EmulatorOrientation.PORTRAIT, playstore=False):
        log.info("Launching emulator...")
        # delete_avd(self.avd_name)  # enable this line to reset upon each start
        if not is_avd_available(self.avd_name):
            self.create_avd(playstore=playstore)
        if not is_avd_config_readable():
            log.warning("AVD configuration is not readable - trying to reset AVD")
            self.delete_avd()
            self.create_avd(playstore=playstore)
            if not is_avd_config_readable():
                raise RuntimeError('AVD configuration unreadable and reset failed.')
        if self.get_orientation() != orientation:
            log.debug(f"Modifying emulator orientation...")
            self.set_orientation(orientation)
        if self.is_playstore_enabled() != playstore:
            log.debug(f"Modifying playstore setting - new setting is \"{playstore}\"")
            self.set_playstore_enabled(playstore)
            # this requires a re-creation of the avd since we need different packages
            self.delete_avd()
            self.create_avd(playstore=playstore)
        if not is_acceleration_available():
            log.warning("Accelerated emulation is NOT available, emulation will be too slow.")
        output = subprocess.run(shlex.split(
            f"{EMU_NAME} -avd {self.avd_name} -accel auto -gpu host "),
            stdout=subprocess.PIPE,
            universal_newlines=True)


if __name__ == '__main__':
    # executed directly as a script
    print("Emulator control")
    emu = Emulator()
    # emu.delete_avd()
    emu.launch_emulator(orientation=EmulatorOrientation.LANDSCAPE, playstore=True)
