from settings_frame import *
from parameter_select_frame import *
from analysis_frame import *
from log_frame import *
from qoemu_pkg.configuration import *


class Gui(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.title("QoEmu GUI")
        self.geometry("1600x900")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH)

        self.parameter_frame = ParameterFrame(self)
        self.settings_frame = SettingsFrame(self)
        self.analysis_frame = AnalysisFrame(self)
        self.log_frame = LogFrame(self)

        notebook.add(self.parameter_frame, text='Parameter Select')
        notebook.add(self.settings_frame, text='Emulation Settings')
        notebook.add(self.analysis_frame, text='Analysis Settings')
        notebook.add(self.log_frame, text='Log')

        # self.parameter_frame.grid(row=0, column=0, sticky="nsew", rowspan=2)
        # self.settings_frame.grid(row=0, column=1, sticky="nsew")
        # self.analysis_frame.grid(row=0, column=2, sticky="nsew")
        # self.log_frame.grid(row=1, column=1, sticky="nsew", columnspan=2)


gui = Gui()
gui.mainloop()
