from tkinter import messagebox

import qoemu_pkg.utils
from qoemu_pkg.gui.emulation_frame import *
from qoemu_pkg.gui.parameter_frame import *
from qoemu_pkg.gui.post_processing_frame import *
from qoemu_pkg.gui.analysis_frame import *
from qoemu_pkg.gui.run_frame import *
from qoemu_pkg.configuration import *
from qoemu_pkg import configuration
import qoemu_pkg.gui.tooltip_strings
from qoemu_pkg import __version__


ELEMENT_LIST_TO_UPDATE = []

GUI_TITLE = f"QoEmu {__version__} "
WINDOW_SIZE = "700x700"
ICON_PATH = os.path.join(os.path.dirname(__file__), 'QoEmuIcon.png')

PARAMETERS_TAB_NAME = 'Parameters'
EMULATION_TAB_NAME = 'Emulation'
POST_PROCESSING_TAB_NAME = 'Post Processing'
ANALYSIS_TAB_NAME = 'Analysis'
RUN_TAB_NAME = 'Run'
TAB_WIDTH = 15
CONFIG_FILE_DESC = "Current config file:"


class Gui(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.tk.call('wm', 'iconphoto', self._w, tk.PhotoImage(file=ICON_PATH))
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        style = ttk.Style()
        style.theme_settings("default", {"TNotebook.Tab": {"configure": {"padding": [10, 2]}}})

        path = os.path.dirname(GUI_DEFAULT_CONFIG_FILE_LOCATION)
        if not os.path.exists(path):
            os.makedirs(path)

        try:
            self.qoemu_config = QoEmuConfiguration(GUI_DEFAULT_CONFIG_FILE_LOCATION)
            self.current_config_path = tk.StringVar()
            self.current_config_path.set(self.qoemu_config.gui_current_config_file.get())
            self.qoemu_config.read_from_file(self.current_config_path.get())
        except RuntimeError:
            self.qoemu_config = QoEmuConfiguration()
            self.current_config_path = tk.StringVar()
            self.current_config_path.set(GUI_DEFAULT_CONFIG_FILE_LOCATION)
            self.qoemu_config.save_to_file(GUI_DEFAULT_CONFIG_FILE_LOCATION)

        self.updatable_elements = []

        self.update_title()
        self.geometry(WINDOW_SIZE)
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
        self.current_config_path_desc = tk.Label(master=self.path_frame, text=CONFIG_FILE_DESC, anchor="w")
        self.current_config_path_desc.pack(fill=tk.BOTH, expand=0, side="left")
        self.current_config_path_label = tk.Label(master=self.path_frame, textvariable=self.current_config_path, anchor="w")
        self.current_config_path_label.pack(fill=tk.BOTH, expand=1, side="left")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.Y, expand=0, side="top")
        self.button_load_default = tk.Button(self.button_frame, text="Open Default Config",
                                             command=self.load_default_config)
        self.button_load_default.pack(fill=tk.X, side="right", expand=2)

        self.button_load_config = tk.Button(self.button_frame, text="Open Config", command=self.load_config)
        self.button_load_config.pack(fill=tk.X, side="right", expand=0)

        self.button_save_config_as = tk.Button(self.button_frame, text="Save Config As", command=self.save_config_as)
        self.button_save_config_as.pack(fill=tk.X, side="right", expand=0)

        self.button_save_config = tk.Button(self.button_frame, text="Save Config", command=self.save_config)
        self.button_save_config.pack(fill=tk.X, side="right", expand=0)

        self.parameter_frame = ParameterFrame(self, self)
        self.run_frame = RunFrame(self, self, self.parameter_frame.get_checked_entries)
        self.settings_frame = EmulationFrame(self, self)
        self.post_processing_frame = PostProcessingFrame(self, self)
        self.analysis_frame = AnalysisFrame(self, self)


        self.notebook.add(self.parameter_frame, text=f'{PARAMETERS_TAB_NAME: ^{TAB_WIDTH}s}')
        self.notebook.add(self.settings_frame, text=f'{EMULATION_TAB_NAME: ^20s}')
        self.notebook.add(self.post_processing_frame, text=f'{POST_PROCESSING_TAB_NAME: ^{TAB_WIDTH}s}')
        self.notebook.add(self.analysis_frame, text=f'{ANALYSIS_TAB_NAME: ^{TAB_WIDTH}s}')
        self.notebook.add(self.run_frame, text=f'{RUN_TAB_NAME: ^{TAB_WIDTH}s}')

    def save_config(self):
        path = os.path.dirname(self.qoemu_config.gui_current_config_file.get())
        if not os.path.exists(path):
            os.makedirs(path)
        self.update_elements_config()
        self.qoemu_config.save_to_file(self.qoemu_config.gui_current_config_file.get())

    def update_elements_display(self):
        for element in self.updatable_elements:
            element.update_display()

    def update_elements_config(self):
        for element in self.updatable_elements:
            element.update_config()

    def load_config(self):
        path_object = filedialog.askopenfile(initialdir=
                                             os.path.dirname(GUI_DEFAULT_CONFIG_FILE_LOCATION),
                                             filetypes=[("config files", "*.conf")])
        if not path_object:
            return
        path = path_object.name
        if not path.endswith(".conf"):
            answer = messagebox.askokcancel("Warning", "This doesn't seem to be a configuration file. Continue?")
            if not answer:
                return

        self.qoemu_config.read_from_file(path)
        self.update_elements_display()
        self.current_config_path.set(path)
        self.update_title()
        self.save_current_config_path_in_default_config(path)

    @staticmethod
    def save_current_config_path_in_default_config(path):
        temp_config = QoEmuConfiguration(GUI_DEFAULT_CONFIG_FILE_LOCATION)
        temp_config.gui_current_config_file.set(path)
        temp_config.save_to_file(GUI_DEFAULT_CONFIG_FILE_LOCATION)

    def save_config_as(self):
        path_object = filedialog.asksaveasfile(initialdir=
                                               os.path.dirname(GUI_DEFAULT_CONFIG_FILE_LOCATION),
                                               filetypes=[("config files", "*.conf")])
        if not path_object:
            return
        path = path_object.name
        if not path.endswith(".conf"):
            path += ".conf"
        self.qoemu_config.gui_current_config_file.set(path)
        self.current_config_path.set(path)
        self.save_config()
        self.save_current_config_path_in_default_config(path)
        self.update_title()

    def load_default_config(self):
        self.qoemu_config.read_from_file(GUI_DEFAULT_CONFIG_FILE_LOCATION)
        self.current_config_path.set(GUI_DEFAULT_CONFIG_FILE_LOCATION)
        self.save_current_config_path_in_default_config(GUI_DEFAULT_CONFIG_FILE_LOCATION)
        self.update_elements_display()
        self.update_title()


    def on_exit(self):
        if self.qoemu_config.modified_since_last_save:
            answer = messagebox.askyesnocancel("Question", "Do you want to save the changes to the current "
                                                           "configuration before closing?")
            if answer is None:
                return
            if answer:
                self.save_config()
                self.exit()
            else:
                self.exit()
        else:
            self.exit()

    def exit(self):
        self.run_frame.terminate_coordinator()
        self.destroy()

    def update_title(self):
        self.title(GUI_TITLE + " - " + os.path.split(self.current_config_path.get())[-1])


def main():
    gui = Gui()
    gui.mainloop()


if __name__ == '__main__':
    main()
