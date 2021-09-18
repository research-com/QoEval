from __future__ import annotations
from subframes import *
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui


class PostProcessingFrame(tk.Frame):
    def __init__(self, master, gui: Gui):
        super().__init__(master, background="#DCDCDC", bd=1, relief=RELIEF)
        self.master = master
        self.gui: Gui = gui

        # VidStartDetectThrSizeNormalRelevance = 10000
        self.vid_start_detect_thr_size_normal_frame = IntegerFrame(self, self.gui,
                                                                   config_variable=
                                                                   self.gui.qoemu_config.
                                                                   vid_start_detect_thr_size_normal_relevance,
                                                                   min_value=0)
        self.vid_start_detect_thr_size_normal_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VidStartDetectThrSizeHighRelevance
        self.vid_start_detect_thr_size_high_frame = IntegerFrame(self, self.gui,
                                                                 config_variable=
                                                                 self.gui.qoemu_config.
                                                                 vid_start_detect_thr_size_high_relevance,
                                                                 min_value=0)
        self.vid_start_detect_thr_size_high_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VidStartDetectThrNrFrames
        self.vid_start_detect_thr_nr_frame = IntegerFrame(self, self.gui,
                                                          config_variable=
                                                          self.gui.qoemu_config.vid_start_detect_thr_nr_frames,
                                                          min_value=0)
        self.vid_start_detect_thr_nr_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AudioTargetVolume
        self.audio_target_volume_frame = FloatFrame(self, self.gui,
                                                    config_variable=
                                                    self.gui.qoemu_config.audio_target_volume)
        self.audio_target_volume_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AudioEraseStartStop
        self.audio_erase_start_stop_frame = AudioStartStopFrame(self, gui=self.gui,
                                                                config_variable=self.gui.qoemu_config.
                                                                audio_erase_start_stop,
                                                                min_value=0)
        self.audio_erase_start_stop_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VideoCapturePath
        self.video_capture_path_frame = FolderFrame(self, self.gui,
                                                    config_variable=self.gui.qoemu_config.video_capture_path)
        self.video_capture_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # TriggerImagePath
        self.trigger_image_path_frame = FolderFrame(self, self.gui,
                                                    config_variable=self.gui.qoemu_config.trigger_image_path)
        self.trigger_image_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)
