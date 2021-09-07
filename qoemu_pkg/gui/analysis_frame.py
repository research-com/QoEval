from __future__ import annotations

import tkinter as tk
from subframes import *
import qoemu_pkg.analysis.analysis as analysis
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui


class AnalysisFrame(tk.Frame):
    def __init__(self, master, gui: Gui):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.gui: Gui = gui

        # TrafficAnalysisPlot
        self.plot_frame = BooleanFrame(self, self.gui,
                                       config_variable=config.traffic_analysis_plot,)
        self.plot_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # TrafficAnalysisLiveVisualization
        self.live_visualization_frame = BooleanFrame(self, self.gui,
                                                     config_variable=config.traffic_analysis_live)
        self.live_visualization_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Histogram Bin Size Frame
        self.bin_size_frame = ListIntegerFrame(self, self.gui,
                                               config_variable=config.traffic_analysis_bin_sizes,
                                               name="Histogram Bin Sizes",
                                               value_name="Bin",
                                               min_value=2)
        self.bin_size_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Plots Frame

        self.bin_size_frame = PlotsFrame(self, self.gui,
                                         config_variable=config.traffic_analysis_plot_settings,
                                         name="Plots to generate",
                                         value_name="Plot")
        self.bin_size_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)
