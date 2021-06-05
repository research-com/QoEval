"""
Handle configuration options
- look for configuration file (parsed with ConfigParser)
- if no option is given, use default value

"""

import os
import pathlib
import configparser
from enum import Enum

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

config = configparser.SafeConfigParser()
config.read(_default_config_file_locations)

if not QOEMU_SECTION in config:
    raise RuntimeError('No configuration file found - not even the default configuration. Check your installation.')

qoemu_conf = config[f'{QOEMU_SECTION}']

net_device_name = qoemu_conf.get('NetDeviceName','eth0')
net_em_sanity_check = qoemu_conf.getboolean('NetEmSanityCheck',True)
vd_path = qoemu_conf.get('AVDPath', _default_avd_path)
video_capture_path = qoemu_conf.get('VideoCapturePath', _default_video_capture_path)
show_device_frame = qoemu_conf.getboolean('ShowDeviceFrame', False)
emulator_type = MobileDeviceType[qoemu_conf.get('EmulatorType', 'none')]
adb_device_serial = qoemu_conf.get('AdbDeviceSerial', '')
audio_device_emu = qoemu_conf.get('AudioDeviceEmu','')
audio_device_real = qoemu_conf.get('AudioDeviceReal','')
traffic_analysis_live = qoemu_conf.getboolean('TrafficAnalysisLiveVisualization', False)
traffic_analysis_plot = qoemu_conf.getboolean('TrafficAnalysisPlot', True)
