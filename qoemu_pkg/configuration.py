"""
Handle configuration options
- look for configuration file (parsed with ConfigParser)
- if no option is given, use default value

"""

import os
import pathlib
import configparser
from enum import Enum
from typing import List

# default file name of configuration file and mandatory section name
QOEMU_CONF = 'qoemu.conf'
QOEMU_SECTION = 'QOEMU'

class MobileDeviceOrientation(Enum):
    PORTRAIT = 'portrait'
    LANDSCAPE = 'landscape'

class MobileDeviceType(Enum):
    NONE = 'none'
    SDK_EMULATOR = 'emulator'
    GENYMOTION = 'genymotion'
    REAL_DEVICE = 'realdevice'


# provide some default values
_default_avd_path = os.path.join(pathlib.Path.home(), 'qoemu_avd')
_default_video_capture_path = os.path.join(pathlib.Path.home(), 'stimuli')

_default_config_file_locations = [os.path.join(os.path.dirname(__file__),QOEMU_CONF),
    f'./{QOEMU_CONF}', os.path.join(pathlib.Path.home(), QOEMU_CONF),
                                  ]

if os.environ.get("QOEMU_CONF"):
    _default_config_file_locations.append(os.environ.get("QOEMU_CONF"))


class QoEmuConfiguration:

    def __init__(self, configparser):
        self.configparser = configparser
        self.vd_path = Option(self, 'AVDPath', _default_avd_path)
        self.video_capture_path = Option(self, 'VideoCapturePath', _default_video_capture_path)
        self.show_device_frame = BoolOption(self, 'ShowDeviceFrame', False)
        self.emulator_type = MobileDeviceTypeOption(self, 'EmulatorType', 'none')
        self.excluded_ports = ListIntOption(self, 'ExcludedPorts', '22,5000,5002')
        self.net_device_name = Option(self, 'NetDeviceName', 'eth0')

        self.adb_device_serial = Option(self, 'AdbDeviceSerial', '')
        self.audio_device_emu = Option(self, 'AudioDeviceEmu', '')
        self.audio_device_real = Option(self, 'AudioDeviceReal', '')
        self.traffic_analysis_live = BoolOption(self, 'TrafficAnalysisLiveVisualization', False)
        self.traffic_analysis_plot = BoolOption(self, 'TrafficAnalysisPlot', True)
        self.net_em_sanity_check = BoolOption(self, 'NetEmSanityCheck', True)


    def save_to_file(self):
        with open(_default_config_file_locations[0], 'w') as configfile:
            self.configparser.write(configfile)


class Option:
    def __init__(self, config: QoEmuConfiguration, option: str, default: str, section: str = QOEMU_SECTION):
        self.config = config
        self.section = section
        self.option = option
        self.default = default
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)

    def get(self):
        return self.value

    def set(self, value: str):
        self.value = value
        self.config.configparser.set(section=self.section, option=self.option, value=self.value)


class BoolOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: bool, section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)
        self.value = self.config.configparser.getboolean(section=self.section, option=self.option, fallback=self.default)

    def get(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = value
        self.config.configparser.setboolean(section=self.section, option=self.option, value=str(self.value))


class MobileDeviceTypeOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: str, section: str = QOEMU_SECTION):
        super().__init__(config, option, default, section)

    def get(self) -> MobileDeviceType:
        return MobileDeviceType[self.value]

    def set(self, value: MobileDeviceType):
        self.value = value.name
        self.config.configparser.set(self.section, self.option, self.value)


class ListIntOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: str, section: str = QOEMU_SECTION):
        super().__init__(config, option, default, section)

    def get(self) -> List[int]:
        excluded_ports = []
        for port in self.value.split(','):
            excluded_ports.append(int(port))
        return excluded_ports

    def set(self, value: List[int]):
        self.value = ",".join([str(i) for i in value])
        self.config.configparser.set(self.section, self.option, self.value)


configparser = configparser.ConfigParser()

configparser.read(_default_config_file_locations)  # note: last file will take precedence in case of overlap

if QOEMU_SECTION not in configparser:
    raise RuntimeError('No configuration file found - not even the default configuration. Check your installation.')

config = QoEmuConfiguration(configparser)


