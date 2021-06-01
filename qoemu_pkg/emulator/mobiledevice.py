"""
    Emulator control

    Base class for emulation control
"""

import logging as log
import subprocess
import ipaddress
import shlex
import re
from qoemu_pkg.configuration import MobileDeviceOrientation, adb_device_serial

if len(adb_device_serial) > 1:
    ADB_NAME = f"adb -s {adb_device_serial}"   #-e selects emulator, -d usb-connected device, -s serialnr
else:
    ADB_NAME = "adb"

MEASUREMENT_TEST_HOST = "www.youtube.de"

def check_ext(name):
    log.debug(f"locating {name}")
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - please install AndroidStudio.")
        raise RuntimeError('External component not found.')
    else:
        log.debug(f"using {output.stdout}")

class MobileDevice:

    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.check_env()
        self.vd_name = None
        self.config = None
        self.envOk = False

    def check_env(self):
        """Checks if the environment is prepared to execute the emulator. Needs to be overriden by subclasses."""
        self.envOk = True

    def is_device_available(self, name: str) -> bool:
        """
        Checks if a (virtual) device is available and could be started.

        Parameters
        ----------
        name : str
           Name of VD to check
        """
        return False

    def is_template_available(self, name: str) -> bool:
        """
        Checks if a template is available.

        Parameters
        ----------
        name : str
           Name of template to check for
        """
        return False

    def download_target(self, name: str):
        """
        Downloads a (missing) target from the repository.

        Parameters
        ----------
        name : str
           Name of target to download
        """
        pass

    def is_device_ready(self, name: str) -> bool:
        """
        Checks if a device is ready and accessible.

        Parameters
        ----------
        name : str
           Name of device to check for
        """
        return False

    def is_acceleration_available(self) -> bool:
        """
        Checks if the emulator can use hardware acceleration.
        """
        return False

    def create_device(self, playstore=False):
        """
        Creates the (virtual) device.

        Parameters
        ----------
        playstore : bool
          Indicates if the playstore API should be installed
        """
        pass

    def delete_device(self):
        """
        Deletes the (virtual) device.
        """
        pass

    def is_playstore_enabled(self) -> bool:
        """
        Checks if the playstore API is enabled for the currently used virtual device.
        """
        return False

    def set_playstore_enabled(self, is_enabled: bool):
        """
        Sets the current availability status for the playstore API.

        Parameters
        ----------
        playstore : bool
          Indicates if the playstore API should be enabled (can only be enable if it was installed during creation)
        """
        pass

    def set_standard_parameters(self):
        """
        Set standard parameters for the current virtual device.
        """
        pass

    def get_orientation(self) -> MobileDeviceOrientation:
        """
        Get currently active orientation of the device
        """
        return MobileDeviceOrientation.PORTRAIT

    def set_orientation(self, orientation: MobileDeviceOrientation):
        pass

    def input_keyevent(self, keyevent: int):
        subprocess.run(shlex.split(f"{ADB_NAME} shell input keyevent {keyevent}")).check_returncode()

    def unlock_device(self):
        self.input_keyevent(82)   # menu
        self.input_keyevent(4)    # back

    def get_ip_address(self) -> ipaddress:
        output = subprocess.run(shlex.split(
            f"{ADB_NAME} shell ifconfig wlan0"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        # log.debug(output.stdout)
        pattern = r"\s*inet addr:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stdout))
        if match:
            ip_addr_text = match.group(1)
            log.debug(f"mobile device ip address: {ip_addr_text}")
            ip_address = ipaddress.ip_address(ip_addr_text)
        else:
            ip_address = None
            log.debug("Cannot determine ip addess of mobile device.")

        return ip_address

    def measure_rtt(self) -> float:
        log.debug(f"Measuring delay bias (target host: {MEASUREMENT_TEST_HOST})...")
        # first ping is ignored (includes times for DNS etc.)
        subprocess.run(shlex.split(f"{ADB_NAME} shell ping -c 6 {MEASUREMENT_TEST_HOST}"), stdout=subprocess.PIPE)
        # now perform the actual measurement
        output = subprocess.run(shlex.split(
            f"{ADB_NAME} shell ping -c 20 -i 0.2 {MEASUREMENT_TEST_HOST}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        pattern = r"\s*rtt min/avg/max/mdev\s*=\s*(\d{1,3}.\d{1,3})/(\d{1,3}.\d{1,3})/(\d{1,3}.\d{1,3})/(\d{1,3}.\d{1,3})\sms"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stdout))
        if match:
            avg_delay = match.group(2)
            log.debug(f"measured delay bias avg: {avg_delay}ms  min: {match.group(1)}ms   max: {match.group(3)}ms")
        else:
            log.error(output.stdout)
            raise RuntimeError("Measuring delay bias failed.")
        return float(avg_delay)

    def launch(self, orientation=MobileDeviceOrientation.PORTRAIT, playstore=False):
        """
        Launch the device

        :param orientation: Orientation to be used
        :param playstore: should the playstore be enabled?
        :return:
        """
        log.error("Launching emulator is not implemented for the Emulator base class")

    def shutdown(self):
        """
        Shutdown the device
        """
        log.error("Shutting down the emulator is not implemented for the Emulator base class")