"""
Handle configuration options
- look for configuration file (parsed with ConfigParser)
- if no option is given, use default value

"""

import os
import pathlib
import configparser

# default file name of configuration file and mandatory section name
from qoemu_pkg.emulator.mobiledevice import MobileDeviceType

QOEMU_CONF = 'qoemu.conf'
QOEMU_SECTION = 'QOEMU'

# provide some default values
_default_avd_path = os.path.join(pathlib.Path.home(), 'qoemu_avd')
_default_video_capture_path = os.path.join(pathlib.Path.home(), 'stimuli')

_default_config_file_locations = [os.path.join(os.path.dirname(__file__), QOEMU_CONF),
                                  f'./{QOEMU_CONF}', os.path.join(pathlib.Path.home(), QOEMU_CONF),
                                  ]

if os.environ.get("QOEMU_CONF"):
    _default_config_file_locations.append(os.environ.get("QOEMU_CONF"))

config = configparser.SafeConfigParser()
config.read(_default_config_file_locations)  # note: last file will take precedence in case of overlap

if QOEMU_SECTION not in config:
    raise RuntimeError('No configuration file found - not even the default configuration. Check your installation.')

qoemu_conf = config[f'{QOEMU_SECTION}']

vd_path = qoemu_conf.get('AVDPath', _default_avd_path)
video_capture_path = qoemu_conf.get('VideoCapturePath', _default_video_capture_path)
show_device_frame = qoemu_conf.get('ShowDeviceFrame', False)
emulator_type = MobileDeviceType[qoemu_conf.get('EmulatorType', 'none')]
excluded_ports = []
for port in qoemu_conf.get('ExcludedPorts').split(','):
    excluded_ports.append(int(port))
pass
pass
