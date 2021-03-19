"""
    Emulator control

    Base class for emulation control
"""

import logging as log
import subprocess
import ipaddress
from enum import Enum


def check_ext(name):
    log.debug(f"locating {name}")
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - please install AndroidStudio.")
        raise RuntimeError('External component not found.')
    else:
        log.debug(f"using {output.stdout}")


class EmulatorOrientation(Enum):
    PORTRAIT = 'portrait'
    LANDSCAPE = 'landscape'

class EmulatorType(Enum):
    NONE = 'none'
    SDK_EMULATOR = 'emulator'
    GENYMOTION = 'genymotion'

class Emulator:

    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.check_env()
        self.vd_name = None
        self.config = None
        self.envOk = False

    def check_env(self):
        """Checks if the environment is prepared to execute the emulator. Needs to be overriden by subclasses."""
        self.envOk = True

    def is_vd_available(self, name: str) -> bool:
        """
        Checks if a virtual device is available.

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

    def is_device_available(self, name: str) -> bool:
        """
        Checks if a device is available.

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

    def create_vd(self, playstore=False):
        """
        Creates the virtual device.

        Parameters
        ----------
        playstore : bool
          Indicates if the playstore API should be installed
        """
        pass

    def delete_vd(self):
        """
        Deletes the virtual device.
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

    def get_orientation(self) -> EmulatorOrientation:
        """
        Get currently active orientation of the device
        """
        return EmulatorOrientation.PORTRAIT

    def set_orientation(self, orientation: EmulatorOrientation):
        pass

    def get_ip_address(self) -> ipaddress:
        pass

    def launch(self, orientation=EmulatorOrientation.PORTRAIT, playstore=False):
        """
        Launche the emulator

        :param orientation: Orientation to be used
        :param playstore: should the playstore be enabled?
        :return:
        """
        log.error("Launching emulator is not implemented for the Emulator base class")

    def shutdown(self):
        """
        Shutdown the emulator
        """
        log.error("Shutting down the emulator is not implemented for the Emulator base class")