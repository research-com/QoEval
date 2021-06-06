#!/usr/bin/env python3
"""
    Device control for a physical Android device
"""
import ipaddress
import threading
import time

from qoemu_pkg.emulator.mobiledevice import check_ext, MobileDevice, MobileDeviceOrientation, ADB_NAME, \
    MEASUREMENT_DURATION
from qoemu_pkg.configuration import vd_path

import logging as log
import subprocess
import shlex
import re

SCREENCOPY_NAME = "scrcpy"
SCREENCOPY_OPTIONS ="--stay-awake"
ADB_NAME = "adb"


class PhysicalDevice(MobileDevice):
    def __init__(self, mirror: bool=True):
        super().__init__()
        self.__scrcpy_output = None
        self.__mirror = mirror

    def check_env(self):
        log.info("checking availability of mobile device mirroring tool...")
        check_ext(SCREENCOPY_NAME)
        self.envOk = True

    def is_device_available(self, name):
        # cannot check if a device is (potentially) available, so we assume, it is
        # (if it is not available, we will fail when checking for readyness)
        return True

    def is_template_available(self, name):
        # templates are not required for physical devices, so the template is virtually available
        return True

    def download_target(self, name):
        log.debug(f"trying to download target {name} - but this is a physical device (ignored)")

    def is_device_ready(self, name):
        log.debug(f"checking if device {name} is ready")
        output = subprocess.run(shlex.split(f"{ADB_NAME} devices"), stdout=subprocess.PIPE,
                                universal_newlines=True)
        return output.stdout.find("\"" + name + "\"") != -1

    def is_acceleration_available(self):
        return True

    def measure_rtt(self) -> float:
        # Note regarding RTT measurements on real physical devices:
        # Most Android phones have a power saving mode for wifi which leads to highly
        # varying delays in times without data traffic. In order to avoid this effect,
        # we send random data to the phone during the RTT measurement procedure
        # so it (hopefully) will not be able to switch to a power saving mode
        traffic_gen_thread = threading.Thread(target=self.generate_udp_traffic, args=(128, 100,MEASUREMENT_DURATION+3))
        traffic_gen_thread.start()
        time.sleep(0.5)
        measured_rtt = super().measure_rtt()
        traffic_gen_thread.join()
        return measured_rtt

    def create_device(self, playstore=False):
        log.debug(f"Trying to create {self.vd_name} - but this is a physical device (ignored)")

    def delete_device(self):
        log.debug(f"Trying to delete {self.vd_name} - but this is a physical device (ignored)")

    def is_playstore_enabled(self) -> bool:
        # TODO: implement real check
        return True

    def set_playstore_enabled(self, is_enabled: bool):
        # TODO: check if we need enabling/disabling playstore on a real device
        pass

    def set_standard_parameters(self):
        pass

    def get_orientation(self):
        output = subprocess.run(shlex.split(
            f"{ADB_NAME} shell dumpsys input"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        # log.debug(output.stdout)
        pattern = r"\s*SurfaceOrientation: (\d)\s*"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stdout))
        if match:
            surface_orientation_number = match.group(1)
            log.debug(f"physical device orientation: {surface_orientation_number}")
        else:
            log.error("Cannot determine orientation of physical device.")
        if surface_orientation_number == 1 or surface_orientation_number == 3:
            return MobileDeviceOrientation.LANDSCAPE
        else:
            return MobileDeviceOrientation.PORTRAIT

    def set_orientation(self, orientation: MobileDeviceOrientation):
        # disable automatic rotation
        subprocess.run(shlex.split(f"{ADB_NAME} shell settings put system accelerometer_rotation 0"))
        if orientation == MobileDeviceOrientation.LANDSCAPE:
            rotation_nr = 1
        else:
            rotation_nr = 0
        # set orientation manually
        subprocess.run(shlex.split(f"{ADB_NAME} shell settings put system user_rotation {rotation_nr}"))

    def launch(self, orientation=MobileDeviceOrientation.PORTRAIT, playstore=True):
        log.info("Launching physical device connection...")
        if self.get_orientation() != orientation:
            log.debug(f"Modifying emulator orientation...")
            self.set_orientation(orientation)
        if self.is_playstore_enabled() != playstore:
            log.debug(f"Modifying playstore setting - new setting is \"{playstore}\"")
            self.set_playstore_enabled(playstore)
        if self.__mirror:
            log.debug("Establishing mobile device mirroring...")
            self.__scrcpy_output = subprocess.Popen(shlex.split(
                f"{SCREENCOPY_NAME} {SCREENCOPY_OPTIONS}"),
                stdout=subprocess.PIPE,
                universal_newlines=True)
            for i in range(0, 5):
                if self.__scrcpy_output.poll() != None and self.__scrcpy_output.poll() != 0:
                    raise RuntimeError(f"Error while launching mobile device screen copy.")
                time.sleep(1)
                log.debug("Waiting for mobile device mirror connection...")

        self.unlock_device()
        self.input_keyevent(3)  # send HOME key so that we are in a defined state
        log.debug("Physical device connection has been launched.")

    def shutdown(self):
        log.debug("Physical device connection shutdown.")
        if self.__scrcpy_output:
            self.__scrcpy_output.terminate()


if __name__ == '__main__':
    # executed directly as a script
    print("physical device control")
    pd = PhysicalDevice()
    pd.launch(orientation=MobileDeviceOrientation.LANDSCAPE, playstore=False)
    ipaddr = pd.get_ip_address()
    rtt = pd.measure_rtt()
    print(f"Physical device IP address: {ipaddr}    RTT bias: {rtt}")
    time.sleep(20)
    pd.shutdown()
