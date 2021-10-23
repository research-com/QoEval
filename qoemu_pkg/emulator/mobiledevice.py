# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
"""
    Emulator control

    Base class for emulation control
"""

import logging as log
import os
import subprocess
import ipaddress
import shlex
import re
import socket
import time

from qoemu_pkg.configuration import MobileDeviceOrientation, QoEmuConfiguration


def adb_name(qoemu_config: QoEmuConfiguration):
    if len(qoemu_config.adb_device_serial.get()) > 1:
        return f"adb -s {qoemu_config.adb_device_serial.get()}"  # -e selects emulator, -d usb-connected device, -s serialnr
    else:
        return "adb"


MEASUREMENT_TEST_HOST = "www.youtube.de"  # target host for RTT tests
MEASUREMENT_DURATION = 3                 # duration of RTT measurement [s]


def check_ext(name):
    log.debug(f"locating {name}")
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - please install and try again.")
        raise RuntimeError('External component not found.')
    else:
        log.debug(f"using {output.stdout}")


class MobileDevice:

    def __init__(self, qoemu_config: QoEmuConfiguration):
        log.basicConfig(level=log.DEBUG)
        self.qoemu_config = qoemu_config
        self.check_env()
        self.vd_name = None
        self.config = None
        self.envOk = False
        self.ip_address = None

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
        is_enabled : bool
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
        subprocess.run(shlex.split(f"{adb_name(self.qoemu_config)} shell input keyevent {keyevent}")).check_returncode()

    def unlock_device(self):
        self.input_keyevent(82)   # menu
        self.input_keyevent(4)    # back

    def get_ip_address(self) -> ipaddress:
        output = subprocess.run(shlex.split(
            f"{adb_name(self.qoemu_config)} shell ifconfig wlan0"),
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

        self.ip_address = ip_address
        return ip_address

    def measure_rtt(self) -> float:
        log.debug(f"Measuring RTT (target host: {MEASUREMENT_TEST_HOST})...")
        # first ping is ignored (includes times for DNS etc.)
        subprocess.run(shlex.split(f"{adb_name(self.qoemu_config)} shell ping -c 1 {MEASUREMENT_TEST_HOST}"),
                       stdout=subprocess.PIPE)
        # now perform the actual measurement
        output = subprocess.run(shlex.split(
            f"{adb_name(self.qoemu_config)} shell ping -c {MEASUREMENT_DURATION/0.2} -i 0.2 {MEASUREMENT_TEST_HOST}"),
            stdout=subprocess.PIPE,
            universal_newlines=True)
        pattern = r"\s*rtt min/avg/max/mdev\s*=\s*(\d{1,4}.\d{1,4})/" \
                  r"(\d{1,4}.\d{1,4})/(\d{1,4}.\d{1,4})/(\d{1,4}.\d{1,4})\sms"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stdout))
        if match:
            avg_delay = match.group(2)
            log.debug(f"measured RTT avg: {avg_delay}ms  min: {match.group(1)}ms   max: {match.group(3)}ms")
        else:
            log.error(output.stdout)
            raise RuntimeError("Measuring RTT failed.")
        return float(avg_delay)

    def generate_udp_traffic(self, packet_size: int = 128, packet_rate=10, duration: float = 10, port: int = 4711):
        """
        Send random UDP packet to this mobile device, i.e. to avoid going into power-saving mode.

        :param packet_size: Size of generated data packets (UDP payload, [byte])
        :param packet_rate: Rate at which packets are generated [pkts/s]
        :param duration: Duration of time-span for which packets a generated.
        :param port: Destination port of sent UDP packets.
        :return:
        """
        if not self.ip_address:
            self.get_ip_address()
        data = bytearray(os.urandom(packet_size))
        inter_tx_interval = 1.0 / packet_rate
        end_time = time.time() + duration
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while time.time() < end_time:
            sock.sendto(data, (str(self.ip_address), port))
            time.sleep(inter_tx_interval)

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
