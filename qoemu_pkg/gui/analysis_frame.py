import tkinter as tk
from config import *
from subframes import *


class AnalysisFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master

        # Label
        # self.label = tk.Label(master=self, text="Analysis Settings", font=("bold", 15), relief="flat")
        # self.label.pack(fill=tk.BOTH, expand=0, side="top")

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
        self.bin_size_frame = BinSizeFrame(self)
        self.bin_size_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # BPF Filter Frame
        self.filter_frame = StringFrame(self,
                                        config_variable=config.traffic_analysis_bpf_filter,
                                        name="Traffic Analysis BPF Rule")
        self.filter_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)


class BinSizeFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        # Label
        self.label = tk.Label(master=self, text="Histogram Bin Sizes (byte)", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        # button Frame
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add_bin = tk.Button(self.button_frame, text="Add Bin",
                                        command=self.add_bin)
        self.button_add_bin.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_delete_bin = tk.Button(self.button_frame, text="Delete Bin",
                                           command=self.delete_bin)
        self.button_delete_bin.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_load_default = tk.Button(self.button_frame, text="Load Default")
        self.button_load_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_set_default = tk.Button(self.button_frame, text="Set Default")
        self.button_set_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.initial_bins = tk.StringVar()
        self.initial_bins.set((1, 2, 3, 4))

        self.listbox = tk.Listbox(self, listvariable=self.initial_bins)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")

    def delete_bin(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

    def add_bin(self):
        try:
            new_bin = int(self.input.get())
            if new_bin not in self.listbox.get(0, "end"):
                self.listbox.insert('end', new_bin)
        except ValueError:
            pass

        self.input.delete(0, "end")
        self.sort_bins()

    def sort_bins(self):
        entries = []
        for entry in self.listbox.get(0, "end"):
            entries.append(entry)
            self.listbox.delete(0)
        entries.sort()
        for entry in entries:
            self.listbox.insert("end", entry)


class FilterFrane(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        # Label
        self.label = tk.Label(master=self, text="BPF Filter Rules", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        # button Frame
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add_bin = tk.Button(self.button_frame, text="Add Rule",
                                        command=self.add_rule)
        self.button_add_bin.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_delete_bin = tk.Button(self.button_frame, text="Delete Rule",
                                           command=self.delete_rule)
        self.button_delete_bin.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_load_default = tk.Button(self.button_frame, text="Load Default")
        self.button_load_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_set_default = tk.Button(self.button_frame, text="Set Default")
        self.button_set_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.initial_bins = tk.StringVar()
        self.initial_bins.set((1, 2, 3, 4))

        self.listbox = tk.Listbox(self, listvariable=self.initial_bins)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")

    def delete_rule(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

    def add_rule(self):
        try:
            rule = self.input.get()
            if rule not in self.listbox.get(0, "end") and rule != "":
                self.listbox.insert('end', rule)
        except ValueError:
            pass

        self.input.delete(0, "end")
