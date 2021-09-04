import tkinter as tk
import psutil
from tkinter import filedialog
from qoemu_pkg.configuration import *
import logging as log
import tooltip
from typing import List
from subframes import *


class PostProcessingFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief=RELIEF)
        self.master = master

        # VidStartDetectThrSizeNormalRelevance = 10000
        self.vid_start_detect_thr_size_normal_frame = IntegerFrame(self,
                                                                   config_variable=
                                                                   config.vid_start_detect_thr_size_normal_relevance,
                                                                   name="Vid Start Detect Threshold Size Normal Relevance",
                                                                   min_value=0)
        self.vid_start_detect_thr_size_normal_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VidStartDetectThrSizeHighRelevance
        self.vid_start_detect_thr_size_high_frame = IntegerFrame(self,
                                                                 config_variable=
                                                                 config.vid_start_detect_thr_size_high_relevance,
                                                                 name="Vid Start Detect Threshold Size High Relevance",
                                                                 min_value=0)
        self.vid_start_detect_thr_size_high_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VidStartDetectThrNrFrames
        self.vid_start_detect_thr_nr_frame = IntegerFrame(self,
                                                          config_variable=
                                                          config.vid_start_detect_thr_nr_frames,
                                                          name="Vid Start Detect Threshold Number of Frames",
                                                          min_value=0)
        self.vid_start_detect_thr_nr_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AudioTargetVolume
        self.audio_target_volume_frame = FloatFrame(self,
                                                    config_variable=
                                                    config.audio_target_volume,
                                                    name="Audio Target Volume")
        self.audio_target_volume_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # VideoCapturePath
        self.video_capture_path_frame = FolderFrame(self,
                                                    config_variable=config.video_capture_path,
                                                    name="Video Capture Path")
        self.video_capture_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # TriggerImagePath
        self.trigger_image_path_frame = FolderFrame(self,
                                                    config_variable=config.trigger_image_path,
                                                    name="DTrigger Image Path")
        self.trigger_image_path_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)
