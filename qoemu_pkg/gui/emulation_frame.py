from __future__ import annotations

import psutil
from qoemu_pkg.gui.subframes import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui


class EmulationFrame(tk.Frame):
    """Frame to control emulation options"""
    def __init__(self, master, gui: Gui):
        super().__init__(master, background="#DCDCDC", bd=1, relief=RELIEF)
        self.master = master
        self.gui: Gui = gui


        # NetDeviceName
        interfaces = list(psutil.net_if_addrs().keys())
        interfaces.remove("lo")
        self.net_device_name_frame = StringSelectFrame(self, self.gui,
                                                       config_variable=self.gui.qoemu_config.net_device_name,
                                                       options=interfaces)
        self.net_device_name_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # MobileDeviceType
        device_types = [e.name for e in MobileDeviceType]
        self.emulator_type_frame = StringSelectFrame(self, self.gui,
                                                     config_variable=self.gui.qoemu_config.emulator_type,
                                                     options=device_types)
        self.emulator_type_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AdbDeviceSerial
        self.adb_device_serial_frame = StringFrame(self, self.gui,
                                                   config_variable=self.gui.qoemu_config.adb_device_serial)
        self.adb_device_serial_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Resolution
        self.resolution_frame = StringSelectFrame(self, self.gui,
                                                  config_variable=self.gui.qoemu_config.resolution_override,
                                                  name="Resolution override",
                                                  options=["off", "Auto", "144p", "240p", "360p", "480p",
                                                           "720p", "1080p"])  # TODO refactor this elsewhere
        self.resolution_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # ShowDeviceFrame
        self.show_device_frame_frame = BooleanFrame(self, self.gui,
                                                    config_variable=self.gui.qoemu_config.show_device_frame)
        self.show_device_frame_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # ShowDeviceScreenMirrorFrame
        self.show_device_screen_mirror_frame = BooleanFrame(self, self.gui,
                                                            config_variable=self.gui.qoemu_config.show_device_screen_mirror)
        self.show_device_screen_mirror_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # NetEmSanityCheck
        self.netem_sanity_check_frame = BooleanFrame(self, self.gui,
                                                     config_variable=self.gui.qoemu_config.net_em_sanity_check)
        self.netem_sanity_check_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AudioDeviceReal
        self.audio_device_real = StringFrame(self, self.gui,
                                             config_variable=self.gui.qoemu_config.audio_device_real)
        self.audio_device_real.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Exclude Ports
        self.exclude_ports_frame = ListIntegerFrame(self, self.gui,
                                                    config_variable=self.gui.qoemu_config.excluded_ports,
                                                    name="Netem Excluded Ports",
                                                    value_name="Port",
                                                    min_value=1, max_value=65535)
        self.exclude_ports_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VideoCapturePath
        self.video_capture_path_frame = FolderFrame(self, self.gui,
                                                    config_variable=self.gui.qoemu_config.video_capture_path)
        self.video_capture_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # DynamicParameterPath
        self.dynamic_parameter_file_path_frame = FolderFrame(self, self.gui,
                                                             config_variable=
                                                             self.gui.qoemu_config.dynamic_parameter_path)
        self.dynamic_parameter_file_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AVDPath
        self.avd_path_frame = FolderFrame(self, self.gui,
                                          config_variable=self.gui.qoemu_config.vd_path)
        self.avd_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)
