#!/usr/bin/env python3
"""
    Emulator control for the emulator which is part of the standard Android SDK
"""
import ipaddress
import time

from qoemu_pkg.emulator.mobiledevice import check_ext, MobileDevice, MobileDeviceOrientation, adb_name
from qoemu_pkg.configuration import config

import logging as log
import configparser
import os
import subprocess
import shlex
import re

# Define constants
TARGET_NAME = "android-30"
DEVICE_NAME = "pixel"
VD_NAME = "qoemu_" + DEVICE_NAME + "_" + TARGET_NAME.replace("-", "_") + "_x86"

EMU_NAME = "emulator"
VD_MANAGER_NAME = "avdmanager"
SDK_MANAGER_NAME = "sdkmanager"
AVD_INI_FILE = f"{config.vd_path.get()}/config.ini"


def is_avd_config_readable() -> bool:
    if os.access(f"{AVD_INI_FILE}", os.R_OK):
        return True
    else:
        return False


class StandardEmulator(MobileDevice):
    def __init__(self):
        super().__init__()
        self.vd_name = VD_NAME

    def __write_avd_config(self):
        log.debug("Writing updated AVD config file")
        new_config = configparser.ConfigParser()
        new_config.optionxform = str
        new_config['config.ini'] = self.config
        # write new config - but remove section header
        config_without_section = '\n'.join(['='.join(item) for item in new_config.items('config.ini')])
        with open(f"{AVD_INI_FILE}", 'w') as f:
            f.write(config_without_section)

    def __read_avd_config(self):
        # note: in order to be able to read the avds config.ini file with configparser
        # we must insert a dummy section
        log.debug("Parsing AVD config file")
        with open(f"{AVD_INI_FILE}", 'r') as f:
            config_string = '[config.ini]\n' + f.read()
        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # default would be to change all options to lowercase
        self.config.read_string(config_string)
        self.config = self.config['config.ini']

    def check_env(self):
        log.info("checking availability of AVD emulator...")
        check_ext(EMU_NAME)
        log.info("checking availability of AVD manager...")
        check_ext(VD_MANAGER_NAME)
        log.info("checking availability of SDK manager...")
        check_ext(SDK_MANAGER_NAME)
        self.envOk = True

    def is_device_available(self, name):
        log.debug(f"checking if AVD {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} list avd"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        if output.stdout.find(name) == -1:
            log.info(f"AVD {name} is NOT available.")
            print(output.stdout)
            return False
        else:
            return True

    def is_template_available(self, name):
        log.debug(f"checking if target {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} list target"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find("\"" + name + "\"") != -1

    def download_target(self, name):
        log.debug(f"downloading target {name}")
        output = subprocess.run(shlex.split(f"{SDK_MANAGER_NAME} --install \"platforms;{name}\""),
                                stdout=subprocess.PIPE,
                                universal_newlines=True)

    def is_device_ready(self, name):
        log.debug(f"checking if device {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} list device"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find("\"" + name + "\"") != -1

    def is_acceleration_available(self):
        output = subprocess.run(shlex.split(f"{EMU_NAME} -accel-check"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find("is installed and usable.") != -1

    def create_device(self, playstore=False):
        log.debug(f"Creating AVD {self.vd_name}")
        # check that the required target and device are available
        if not self.is_template_available(TARGET_NAME):
            self.download_target(TARGET_NAME)
            if not self.is_template_available(TARGET_NAME):
                raise RuntimeError('Downloading the required target failed.')
        # use avdmanager to create AVD
        # note: in order to be able to enable playstore, package must include "google_apis_playstore"
        if playstore:
            package = f'system-images;{TARGET_NAME};google_apis_playstore;x86'
        else:
            package = f'system-images;{TARGET_NAME};google_apis;x86'

        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} create avd --package {package} --path {config.vd_path.get()} " +
            f"--device \"{DEVICE_NAME}\" --name {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()
        self.set_standard_parameters()

    def delete_device(self):
        log.debug(f"Deleting AVD {self.vd_name}")
        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} delete avd --name {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def is_playstore_enabled(self) -> bool:
        if not self.config:
            self.__read_avd_config()
        if self.config.get('PlayStore.enabled', 'no') == 'yes':
            return True
        else:
            return False

    def set_playstore_enabled(self, is_enabled: bool):
        if not self.config:
            self.__read_avd_config()
        if is_enabled:
            new_value = 'yes'
        else:
            new_value = 'no'
        self.config['PlayStore.enabled'] = new_value
        self.__write_avd_config()

    def set_standard_parameters(self):
        if not self.config:
            self.__read_avd_config()
        self.config['hw.lcd.density'] = '480'
        self.config['hw.keyboard'] = 'yes'
        self.config['hw.gpu.enabled'] = 'yes'
        self.config['hw.gpu.mode'] = 'host'
        self.config['fastboot.forceColdBoot'] = 'yes'
        self.config['fastboot.forceFastBoot'] = 'no'
        self.config['hw.cpu.ncore'] = '4'
        self.config['hw.ramSize'] = '4096'
        self.__write_avd_config()

    def get_orientation(self):
        if not self.config:
            self.__read_avd_config()
        if self.config.get('hw.initialOrientation', 'portrait') == 'landscape':
            return MobileDeviceOrientation.LANDSCAPE
        else:
            return MobileDeviceOrientation.PORTRAIT

    def set_orientation(self, orientation: MobileDeviceOrientation):
        if not self.config:
            self.__read_avd_config()
        self.config['hw.initialOrientation'] = orientation.value
        self.config['skin.dynamic'] = 'yes'
        # show_device_frame = False
        if config.show_device_frame.get():
            self.config['showDeviceFrame'] = 'yes'
            self.config['skin.name'] = 'pixel_silver'
            self.config['skin.path'] = '/home/qoe-user/Android/Sdk/skins/pixel_silver'  # FIXME: abs path
            self.config['skin.path.backup'] = '_no_skin'
        else:
            self.config['showDeviceFrame'] = 'no'
            self.config['skin.name'] = '1920x1080'
            self.config['skin.path'] = '_no_skin'
            self.config['skin.path.backup'] = '_no_skin'
        self.__write_avd_config()

    def launch(self, orientation=MobileDeviceOrientation.PORTRAIT, playstore=False):
        log.info("Launching emulator...")
        # delete_avd(self.avd_name)  # enable this line to reset upon each start
        if not self.is_device_available(self.vd_name):
            self.create_device(playstore=playstore)
        if not is_avd_config_readable():
            log.warning("AVD configuration is not readable - trying to reset AVD")
            self.delete_device()
            self.create_device(playstore=playstore)
            if not is_avd_config_readable():
                raise RuntimeError('AVD configuration unreadable and reset failed.')
        if self.get_orientation() != orientation:
            log.debug(f"Modifying emulator orientation...")
            self.set_orientation(orientation)
        if self.is_playstore_enabled() != playstore:
            log.debug(f"Modifying playstore setting - new setting is \"{playstore}\"")
            self.set_playstore_enabled(playstore)
            # this requires a re-creation of the avd since we need different packages
            self.delete_device()
            self.create_device(playstore=playstore)
        if not self.is_acceleration_available():
            log.warning("Accelerated emulation is NOT available, emulation will be too slow.")
        output = subprocess.Popen(shlex.split(
            f"{EMU_NAME} -avd {self.vd_name} -accel auto -gpu host "),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        while output.poll() is None and self.get_ip_address() is None:
            log.debug("Emulator does not yet have a valid IP address - waiting...")
            time.sleep(5)
        log.debug("Emulator has been launched.")

    def shutdown(self):
        log.debug("Emulator shutdown.")
        subprocess.run(shlex.split(f"{adb_name()} emu kill"))


if __name__ == '__main__':
    # executed directly as a script
    print("Emulator control")
    emu = StandardEmulator()
    # emu.delete_vd()
    emu.launch(orientation=MobileDeviceOrientation.LANDSCAPE, playstore=False)
    ipaddr = emu.get_ip_address()
    print(f"Emulator IP address: {ipaddr}")
    time.sleep(20)
    emu.shutdown()
