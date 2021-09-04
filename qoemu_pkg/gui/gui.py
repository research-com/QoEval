from settings_frame import *
from parameter_select_frame import *
from post_processing_frame import *
from analysis_frame import *
from run_frame import *
import qoemu_pkg.configuration as config
import tooltip_strings


class Gui(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.title("QoEmu GUI")
        self.geometry("900x900")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=1)

        # Load/Save Config Frame

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.Y, expand=0, side="top")

        self.button_load_default = tk.Button(self.button_frame, text="Load Config")
        self.button_load_default.pack(fill=tk.X, side="right", expand=2)

        self.button_set_default = tk.Button(self.button_frame, text="Save Config")
        self.button_set_default.pack(fill=tk.X, side="right", expand=0)

        self.parameter_frame = ParameterFrame(self)
        self.settings_frame = SettingsFrame(self)
        self.post_processing_frame = PostProcessingFrame(self)
        self.analysis_frame = AnalysisFrame(self)
        self.run_frame = RunFrame(self)

        self.notebook.add(self.parameter_frame, text='Parameter Select')
        self.notebook.add(self.settings_frame, text='Emulation')
        self.notebook.add(self.post_processing_frame, text='Post Processing')
        self.notebook.add(self.analysis_frame, text='Analysis')
        self.notebook.add(self.run_frame, text='Run')


def main():
    gui = Gui()
    gui.mainloop()


if __name__ == '__main__':
    main()
