"""
Handle configuration options
- look for configuration file (parsed with ConfigParser)
- if no option is given, use default value

"""
import ast
import os
import pathlib
import configparser
from enum import Enum
from typing import List, Union, Dict
from qoemu_pkg.gui.tooltip_strings import add_tooltips

# default file name of configuration file and mandatory section name
import qoemu_pkg.analysis.analysis

QOEMU_CONF = 'qoemu.conf'
QOEMU_SECTION = 'QOEMU'
NETEM_SECTION = 'NETEM'
VALUE_SEPERATOR = ";"


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

_default_config_file_locations = [os.path.join(os.path.dirname(__file__), QOEMU_CONF),
                                  f'./{QOEMU_CONF}', os.path.join(pathlib.Path.home(), QOEMU_CONF),
                                  ]

if os.environ.get("QOEMU_CONF"):
    _default_config_file_locations.append(os.environ.get("QOEMU_CONF"))


class QoEmuConfiguration:

    def __init__(self, configparser: configparser.ConfigParser):
        self.modified_since_last_save = False
        self.configparser = configparser

        # general options and paths
        self.vd_path = Option(self, 'AVDPath', _default_avd_path, expand_user=True)
        self.video_capture_path = Option(self, 'VideoCapturePath', _default_video_capture_path, expand_user=True)
        self.trigger_image_path = Option(self, 'TriggerImagePath', '.', expand_user=True)
        self.parameter_file = Option(self, 'ParameterFile', './parameters.csv', expand_user=True)
        self.dynamic_parameter_path = Option(self, 'DynamicParameterPath', '.', expand_user=True)

        self.coordinator_generate_stimuli = BoolOption(self, "CoordinatorGenerateStimuli", True)
        self.coordinator_postprocessing = BoolOption(self, "CoordinatorPostprocessing", False)
        self.coordinator_overwrite = BoolOption(self, "CoordinatorOverwrite", False)

        self.gui_coordinator_stimuli = ListDictOption(self, "CoordinatorStimuliToGenerate", [])
        self.gui_current_config_file = Option(self, "GUIConfigFile", "~/.config/qoemu/qoemu_gui.conf", expand_user=True)

        # capturing options
        self.show_device_frame = BoolOption(self, 'ShowDeviceFrame', False)
        self.show_device_screen_mirror = BoolOption(self, 'ShowDeviceScreenMirror', True)
        self.emulator_type = MobileDeviceTypeOption(self, 'EmulatorType', 'none')
        self.net_device_name = Option(self, 'NetDeviceName', 'eth0')
        self.resolution_override = Option(self, 'ResolutionOverride', "")

        self.adb_device_serial = Option(self, 'AdbDeviceSerial', '')
        self.audio_device_emu = Option(self, 'AudioDeviceEmu', '')
        self.audio_device_real = Option(self, 'AudioDeviceReal', '')

        # network emulation options
        self.excluded_ports = ListIntOption(self, 'ExcludedPorts', [22, 5000, 5002])
        self.net_device_name = Option(self, 'NetDeviceName', 'eth0')
        self.traffic_analysis_live = BoolOption(self, 'TrafficAnalysisLiveVisualization', False)
        self.traffic_analysis_plot = BoolOption(self, 'TrafficAnalysisPlot', True)
        self.traffic_analysis_bin_sizes = ListIntOption(self, "TrafficAnalysisBinSizes", [])
        self.traffic_analysis_plot_settings = ListDictOption(self, 'TrafficAnalysisPlotSettings', [])

        self.net_em_sanity_check = BoolOption(self, 'NetEmSanityCheck', True)

        # post-processing options
        self.vid_start_detect_thr_size_normal_relevance = IntOption(self, 'VidStartDetectThrSizeNormalRelevance', 10000)
        self.vid_start_detect_thr_size_high_relevance = IntOption(self, 'VidStartDetectThrSizeHighRelevance', 40000)
        self.vid_start_detect_thr_nr_frames = IntOption(self, 'VidStartDetectThrNrFrames', 3)
        self.vid_erase_box = ListIntOption(self, 'VidEraseBox', [])
        self.vid_init_buffer_time_manual = FloatOption(self, 'VidInitBufferTimeManual', None)

        self.audio_target_volume = FloatOption(self, 'AudioTargetVolume', -2.0)
        self.audio_erase_start_stop = ListFloatOption(self, 'AudioEraseStartStop', [])

        # post-processing options for specific use-case: application launch
        self.app_launch_additional_recording_duration = FloatOption(self, 'AppLaunchAdditionalRecordingDuration', 0.0)
        self.app_launch_vid_erase_box = ListIntOption(self, 'AppLaunchVidEraseBox', "")

        # post-processing options for specific use-case: web browsing
        self.web_browse_additional_recording_duration = FloatOption(self, 'WebBrowseAdditionalRecordingDuration', 0.0)
        self.web_browse_vid_erase_box = ListIntOption(self, 'WebBrowseVidEraseBox', "")

        add_tooltips(self)

    def save_to_file(self, file: str = None):
        if file is not None:
            file_path = file
        else:
            file_path = _default_config_file_locations[0]

        with open(file_path, 'w') as configfile:
            self.configparser.write(configfile)
        self.modified_since_last_save = False

    def read_from_file(self, file: str = None):
        if file is not None:
            file_path = file
        else:
            file_path = _default_config_file_locations
        self.configparser.read(file_path)
        # print({section: dict(self.configparser[section]) for section in self.configparser.sections()})

    def store_netem_params(self, emulation_parameters):
        for p in emulation_parameters:
            if isinstance(emulation_parameters[p], float):
                FloatOption(self, p, 0.0, NETEM_SECTION).set(emulation_parameters[p])
            else:
                Option(self, p, "", NETEM_SECTION).set(emulation_parameters[p])


class Option:
    def __init__(self, config: QoEmuConfiguration, option: str, default, section: str = QOEMU_SECTION,
                 expand_user: bool = False):
        self.config: QoEmuConfiguration = config
        self.section: str = section
        self.option: str = option
        self.default: str = default
        self.value: str = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        self.expand_user: bool = expand_user
        self.tooltip: str = ""

    def get(self):
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        if self.expand_user:
            return os.path.expanduser(self.value)
        return self.value

    def set(self, value: str):
        self.config.modified_since_last_save = True
        if self.expand_user:
            self.value = value.replace(os.path.expanduser('~'), '~', 1)
        else:
            self.value = value
        self.config.configparser.set(section=self.section, option=self.option, value=self.value)


class BoolOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: bool, section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)
        self.value = self.config.configparser.getboolean(section=self.section, option=self.option,
                                                             fallback=self.default)
        self.default = default

    def get(self) -> bool:
        self.value = self.config.configparser.getboolean(section=self.section, option=self.option, fallback=self.default)
        return self.value

    def set(self, value: bool):
        self.config.modified_since_last_save = True
        self.value = str(value)
        self.config.configparser.set(section=self.section, option=self.option, value=str(self.value))


class IntOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: int, section: str = QOEMU_SECTION):
        super().__init__(config, option, default, section)
        self.value = self.config.configparser.getint(section=self.section, option=self.option, fallback=self.default)
        self.default = default

    def get(self) -> int:
        self.value = int(self.config.configparser.get(section=self.section, option=self.option, fallback=self.default))
        return self.value

    def set(self, value: int):
        self.config.modified_since_last_save = True
        self.value = value
        self.config.configparser.set(section=self.section, option=self.option, value=str(self.value))


class FloatOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: float, section: str = QOEMU_SECTION):
        super().__init__(config, option, default, section)
        self.value = self.config.configparser.getfloat(section=self.section, option=self.option, fallback=self.default)
        self.default = default

    def get(self) -> float:
        self.value = float(self.config.configparser.get(section=self.section, option=self.option, fallback=self.default))
        return self.value

    def set(self, value: float):
        self.config.modified_since_last_save = True
        self.value = value
        self.config.configparser.set(section=self.section, option=self.option, value=str(self.value))


class MobileDeviceTypeOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: str, section: str = QOEMU_SECTION):
        super().__init__(config, option, default, section)

    def get(self) -> MobileDeviceType:
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        return MobileDeviceType[self.value]

    def set(self, value: Union[MobileDeviceType, str]):
        self.config.modified_since_last_save = True
        if type(value) == MobileDeviceType:
            self.value = value.name
        else:
            self.value = value
        self.config.configparser.set(self.section, self.option, self.value)


class ListIntOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: List[int], section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)

    def get(self) -> List[int]:
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        return ast.literal_eval(self.value)

    def set(self, value: List[int]):
        self.config.modified_since_last_save = True
        self.value = str(value)
        self.config.configparser.set(self.section, self.option, self.value)


class ListFloatOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: List[float], section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)

    def get(self) -> List[float]:
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        result = ast.literal_eval(self.value)
        result = [float(value) for value in result]
        return result

    def set(self, value: List[float]):
        self.config.modified_since_last_save = True
        self.value = str(value)
        self.config.configparser.set(self.section, self.option, self.value)


class ListOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: List[str], section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)
        self.default = default

    def get(self) -> List[str]:
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        return ast.literal_eval(self.value)

    def set(self, value: List[str]):
        self.config.modified_since_last_save = True
        self.value = str(value)
        self.config.configparser.set(self.section, self.option, self.value)


class ListDictOption(Option):
    def __init__(self, config: QoEmuConfiguration, option: str, default: List[Dict], section: str = QOEMU_SECTION):
        super().__init__(config, option, str(default), section)

    def get(self) -> List[Dict]:
        self.value = self.config.configparser.get(section=self.section, option=self.option, fallback=self.default)
        return ast.literal_eval(self.value)

    def set(self, value: List[Dict]):
        self.config.modified_since_last_save = True
        self.value = str(value)
        self.config.configparser.set(self.section, self.option, self.value)


def get_default_qoemu_config() -> QoEmuConfiguration:
    parser = configparser.ConfigParser()
    parser.optionxform = str

    # To keep comments:
    # parser = configparser.ConfigParser(comment_prefixes='/', allow_no_value = True)
    # Alternative to consider
    # parser = configupdater.ConfigUpdater()

    parser.read(_default_config_file_locations)  # note: last file will take precedence in case of overlap
    if QOEMU_SECTION not in parser:
        raise RuntimeError('No configuration file found - not even the default configuration. Check your installation.')
    config = QoEmuConfiguration(parser)
    return config
