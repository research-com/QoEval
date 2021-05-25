import logging
import tkinter as tk
from tkinter import ttk
from logging import Handler, getLogger
import qoemu_pkg.coordinator as coord
import threading


class LogFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.thread = None
        self.stop_flag = False

        # Label
        self.label = tk.Label(master=self, text="Log", font=("bold", 15), relief="flat")
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        # Button Frame
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="top")

        # Log level
        self.loglevel = tk.StringVar(self)
        self.loglevel.trace("w", self.change_log_level)
        self.loglevel.set("DEBUG")

        levels = ["INFO", "DEBUG"]

        self.label = tk.Label(master=self.button_frame, text="Log Level: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self.button_frame, self.loglevel, *levels)
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="left")

        # button
        self.button_set_default = tk.Button(self.button_frame, text="Run Coordinator", command=self.start_thread)
        self.button_set_default.pack(fill=tk.BOTH, side="left", expand=1)

        # button
        self.button_set_default = tk.Button(self.button_frame, text="Stop Coordinator", command=self.stop_thread)
        self.button_set_default.pack(fill=tk.BOTH, side="left", expand=1)

        # Log Box
        self.listbox = tk.Text(self)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")

        # Scrollbar Log Box
        listbox_scroll_v = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=listbox_scroll_v.set)
        listbox_scroll_v.pack(fill=tk.BOTH, side="right")

        # Logger
        self.logger = getLogger()
        # add handler to the root logger here
        # should be done in the config...
        self.logger.addHandler(ListboxHandler(self.listbox))
        self.logger.setLevel(logging.DEBUG)

    def change_log_level(self, *args):
        if self.loglevel.get() == "DEBUG":
            self.logger.setLevel(logging.DEBUG)
        if self.loglevel.get() == "INFO":
            self.logger.setLevel(logging.INFO)

    def stop_thread(self):
        self.stop_flag = True

    def start_thread(self):

        self.thread = threading.Thread(target=self.run_coord)
        self.thread.setDaemon(True)
        self.thread.start()

    def run_coord(self):
        # executed directly as a script
        print("Coordinator main started")
        coord.load_parameter_file('/home/jk/PycharmProjects/qoemu/stimuli-params/full.csv')
        print(coord.get_type_ids())
        print(coord.get_table_ids('VS'))
        print(coord.get_entry_ids('VS', 'B'))

        #    print(get_link('VS', 'A', '1'))
        #    print(get_start('VS', 'A', '1'))
        #    print(get_end('VS', 'A', '1'))

        ids_to_evaluate = coord.get_entry_ids('VS', 'B')

        # for id in ids_to_evaluate:
        for id in ['6', '5', '4', '3', '2', '1']:
            coordinator = coord.Coordinator()
            try:
                coordinator.prepare('VS', 'B', id)
                coord.wait_countdown(20)
                coordinator.execute('00:03:00')
                coord.wait_countdown(30)
            finally:
                coordinator.finish()
                if self.stop_flag:
                    self.stop_flag = False
                    return


class ListboxHandler(Handler):
    def __init__(self, box):
        self._box = box
        Handler.__init__(self)

    def emit(self, record):
        r = self.format(record) + "\n"
        self._box.insert("end", r)
        self._box.yview(tk.END)
