from emulation_frame import *
from parameter_select_frame import *
from post_processing_frame import *
from analysis_frame import *
from run_frame import *
from qoemu_pkg.configuration import *
from qoemu_pkg import configuration
import tooltip_strings

CONFIG_FILE = "qoemu_gui.conf"
DEFAUL_CONFIG_FILE = os.path.join(os.path.realpath(os.path.dirname(qoemu_pkg.__file__)),
                                  configuration.QOEMU_CONF)

ELEMENT_LIST_TO_UPDATE = []


class Gui(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.current_config_path = tk.StringVar()
        self.current_config_path.set((os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE)))
        config.read_from_file(self.current_config_path.get())

        self.updatable_elements = []

        self.title("QoEmu GUI")
        self.geometry("700x700")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=1)

        # Load/Save Config

        self.path_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.path_frame.pack(fill=tk.X, expand=0, side="top")
        self.current_config_path_desc = tk.Label(master=self.path_frame, text="Config file: ", anchor="w")
        self.current_config_path_desc.pack(fill=tk.BOTH, expand=0, side="left")
        self.current_config_path_label = tk.Label(master=self.path_frame, textvariable=self.current_config_path, anchor="w")
        self.current_config_path_label.pack(fill=tk.BOTH, expand=1, side="left")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.Y, expand=0, side="top")
        self.button_load_default = tk.Button(self.button_frame, text="Load Default Config",
                                             command=self.load_default_config)
        self.button_load_default.pack(fill=tk.X, side="right", expand=2)

        self.button_save_config = tk.Button(self.button_frame, text="Save Config", command=self.save_config)
        self.button_save_config.pack(fill=tk.X, side="right", expand=0)



        self.parameter_frame = ParameterFrame(self, self)
        self.settings_frame = EmulationFrame(self, self)
        self.post_processing_frame = PostProcessingFrame(self, self)
        self.analysis_frame = AnalysisFrame(self, self)
        self.run_frame = RunFrame(self, self, self.parameter_frame.get_checked_entries)

        self.notebook.add(self.parameter_frame, text='Parameter Select')
        self.notebook.add(self.settings_frame, text='   Emulation    ')
        self.notebook.add(self.post_processing_frame, text='Post Processing ')
        self.notebook.add(self.analysis_frame, text='    Analysis    ')
        self.notebook.add(self.run_frame, text='      Run       ')

    @staticmethod
    def save_config():
        config.save_to_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE))

    def load_default_config(self):
        config.read_from_file(DEFAUL_CONFIG_FILE)
        for element in self.updatable_elements:
            element.update()


def main():
    gui = Gui()
    gui.mainloop()


if __name__ == '__main__':
    main()
