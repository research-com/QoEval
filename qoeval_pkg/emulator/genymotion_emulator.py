#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
"""
    Emulator control for the Genymotion Desktop emulator
"""
import time

from qoeval_pkg.emulator.mobiledevice import check_ext, MobileDevice, MobileDeviceOrientation, adb_name
from qoeval_pkg.configuration import QoEvalConfiguration
import logging as log
import subprocess
import shlex
import ipaddress
import re

VD_MANAGER_NAME = "gmtool"
GM_SHELL = "genymotion-shell"
TEMPLATE_UUID = "c259202b-6605-44eb-978c-040b2edbc364"  # "Google Pixel 3 - 10.0 - API 29 - 1080x2160"
DEVICE_NAME = "pixel"
VD_NAME = "qoeval_" + DEVICE_NAME + "_" + "_Genymotion" + "_x86"
STANDARD_OPTIONS = "--virtualkeyboard=on --nbcpu=6 --ram=4096 --network-mode=nat"


class GenymotionEmulator(MobileDevice):
    def __init__(self, qoeval_config: QoEvalConfiguration):
        super().__init__(qoeval_config)
        self.vd_name = VD_NAME
        self.__orientation = MobileDeviceOrientation.PORTRAIT

    @staticmethod
    def __print_available_templates():
        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin templates --full -f"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        print(output.stdout)

    def check_env(self):
        log.info("checking availability of Genymotion VD manager...")
        check_ext(VD_MANAGER_NAME)
        self.envOk = True

    def delete_device(self):
        log.debug(f"Deleting VD {self.vd_name}")
        subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin stop {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin delete {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def is_device_available(self, name):
        log.debug(f"checking if virtual device {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} admin list"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find(name) != -1

    def is_device_ready(self, name):
        log.debug(f"checking if device {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} admin list --running"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find(name) != -1

    def is_template_available(self, name):
        log.debug(f"checking if template {name} is available")
        output = subprocess.run(shlex.split(f"{VD_MANAGER_NAME} admin templates --full"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        # print (output.stdout)
        return output.stdout.find(name) != -1

    def set_standard_parameters(self):
        log.debug(f"setting standard parameters for {self.vd_name} ")
        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin edit {self.vd_name} {STANDARD_OPTIONS}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()

    def create_device(self, playstore=False):
        log.debug(f"Creating VD {self.vd_name}")
        # check that the required target and device are available
        if not self.is_template_available(TEMPLATE_UUID):
            raise RuntimeError(f'Required template {TEMPLATE_UUID} is not available.')

        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin create {TEMPLATE_UUID} {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()
        self.set_standard_parameters()

    def get_orientation(self):
        return self.__orientation

    def set_orientation(self, orientation: MobileDeviceOrientation):
        log.debug(f"setting orientation for {self.vd_name} ")
        if orientation == MobileDeviceOrientation.PORTRAIT:
            rotation_angle = 0
        elif orientation == MobileDeviceOrientation.LANDSCAPE:
            rotation_angle = 90
        else:
            raise RuntimeError("Not a valid MobileDeviceOrientation")
        output = subprocess.run(shlex.split(
            f"{GM_SHELL} -c \"rotation setangle {rotation_angle}\""),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()
        self.__orientation = orientation

    # alternative implementation using GM_SHELL (should not be necessary)
    # def get_ip_address(self) -> ipaddress:
    #     output = subprocess.run(shlex.split(
    #         f"{GM_SHELL} -c \"devices list\""),
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     output.check_returncode()
    #     # log.debug(output.stdout)
    #     pattern = r"\*\s+\|\s+On.\|\s+virtual\s+\|\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    #     matcher = re.compile(pattern)
    #     match = (matcher.search(output.stdout))
    #     if match:
    #         ip_addr_text = match.group(1)
    #         log.debug(f"emulator ip address: {ip_addr_text}")
    #         ip_address = ipaddress.ip_address(ip_addr_text)
    #     else:
    #         ip_address = None
    #         log.error("Cannot determine ip addess of emulator.")
    #
    #     return ip_address

    def get_ip_address(self) -> ipaddress:
        output = subprocess.run(shlex.split(
            f"{adb_name()} shell ifconfig wlan0"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        # log.debug(output.stdout)
        pattern = r"\s*inet addr:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stdout))
        if match:
            ip_addr_text = match.group(1)
            log.debug(f"emulator ip address: {ip_addr_text}")
            ip_address = ipaddress.ip_address(ip_addr_text)
        else:
            ip_address = None
            log.debug("Cannot determine ip addess of emulator.")

        return ip_address

    def launch(self, orientation=MobileDeviceOrientation.PORTRAIT, playstore=False):
        log.info("Launching emulator...")
        # delete_avd(self.vd_name)  # enable this line to reset upon each start
        if not self.is_device_available(self.vd_name):
            self.create_device(playstore=playstore)
        if self.is_playstore_enabled() != playstore:
            log.debug(f"Modifying playstore setting - new setting is \"{playstore}\"")
            self.set_playstore_enabled(playstore)
            # this requires a re-creation of the avd since we need different packages
            self.delete_device()
            self.create_device(playstore=playstore)
        output = subprocess.run(shlex.split(
            f"{VD_MANAGER_NAME} admin start {self.vd_name}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        output.check_returncode()
        self.set_orientation(orientation)
        while self.get_ip_address() is None:
            log.debug("Emulator does not yet have a valid IP address - waiting for DHCP to be completed...")
            time.sleep(5)

    def shutdown(self):
        log.debug("Emulator shutdown.")
        subprocess.run(shlex.split(f"{VD_MANAGER_NAME} admin stop {self.vd_name}"),)


if __name__ == '__main__':
    # executed directly as a script
    print("Emulator control")
    emu = GenymotionEmulator(QoEvalConfiguration())
    # emu.delete_vd()
    emu.launch(orientation=MobileDeviceOrientation.LANDSCAPE, playstore=False)
    print(f"Started emulator with IP address: {emu.get_ip_address()}")
    time.sleep(20)
    emu.shutdown()
