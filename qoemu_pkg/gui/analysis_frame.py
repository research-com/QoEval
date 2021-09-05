import tkinter as tk
from subframes import *
import qoemu_pkg.analysis.analysis as analysis


class AnalysisFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master

        # TrafficAnalysisPlot
        self.plot_frame = BooleanFrame(self,
                                       config_variable=config.traffic_analysis_plot,
                                       name="Generate Traffic Analysis Plot")
        self.plot_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # TrafficAnalysisLiveVisualization
        self.live_visualization_frame = BooleanFrame(self,
                                                     config_variable=config.traffic_analysis_live,
                                                     name="Live Traffic Analysis")
        self.live_visualization_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Histogram Bin Size Frame
        self.bin_size_frame = IntegerListFrame(self, config_variable=config.traffic_analysis_bin_sizes,
                                               name="Histogram Bin Sizes",
                                               value_name="Bin",
                                               min_value=2)
        self.bin_size_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Plots Frame

        self.bin_size_frame = PlotsFrame(self, config_variable=config.traffic_analysis_plot_sets,
                                              name="Plots to create",
                                              value_name="Plot")
        self.bin_size_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

