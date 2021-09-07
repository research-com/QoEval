from __future__ import annotations

import logging
import subprocess
import tkinter as tk
from tkinter import ttk
from logging import Handler, getLogger

import qoemu_pkg.gui.gui
from qoemu_pkg.coordinator import Coordinator
import threading
from typing import Callable, List, Optional
from subframes import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui


class RunFrame(tk.Frame):
    def __init__(self, master, gui: Gui, get_checked_entries: Callable[[], List[str]]):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.thread = None
        self.get_checked_entries = get_checked_entries
        self.gui: Gui = gui
        self.coordinator_process: Union[subprocess.Popen, None] = None



        self.logger = getLogger()

        # Options
        self.checkbox_frame = CheckboxToBooleanFrame(self, self.gui,
                                                     config_variables=[config.coordinator_generate_stimuli,
                                                                       config.coordinator_postprocessing,
                                                                       config.coordinator_overwrite],
                                                     name="Options",
                                                     variable_names=["Generate Stimuli", "Post Processing",
                                                                     "Overwrite"])
        self.checkbox_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

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

        # Run Coordinator button
        self.button_run_coordinator = tk.Button(self.button_frame, text="Run Coordinator", command=self.start_coordinator)
        self.button_run_coordinator.pack(fill=tk.BOTH, side="left", expand=1)

        # Stop Coordinator button
        self.button_stop_coordinator = tk.Button(self.button_frame, text="Stop Coordinator", command=self.terminate_coordinator)
        self.button_stop_coordinator.pack(fill=tk.BOTH, side="left", expand=1)
        self.button_stop_coordinator["state"] = tk.DISABLED

        # Log Box
        self.listbox = tk.Text(self)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")

        # Scrollbar Log Box
        listbox_scroll_v = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=listbox_scroll_v.set)
        listbox_scroll_v.pack(fill=tk.BOTH, side="right")

        # Logger
        # self.logger = getLogger()
        # add handler to the root logger here
        # should be done in the config...
        self.logger.addHandler(ListboxHandler(self.listbox))
        self.logger.setLevel(logging.DEBUG)

    def change_log_level(self, *args):
        if self.loglevel.get() == "DEBUG":
            self.logger.setLevel(logging.DEBUG)
        if self.loglevel.get() == "INFO":
            self.logger.setLevel(logging.INFO)

    def terminate_coordinator(self):
        self.coordinator_process.terminate()
        log.info("Sent SIGTERM to coordinator process. Waiting for it to terminate")
        self.coordinator_process.wait()
        self.enable_interface_after_coordinator()
        log.info("Coordinator process terminated")

    def start_coordinator(self):
        entries = self.get_checked_entries()
        if len(entries) < 1:
            log.info("No Parameters are selected")
            return

        log.info("Starting coordinator")
        self.disable_interface_for_coordinator()

        entry_list = []
        for entry in entries:
            dictionary = {"type_id": entry[0], "table_id": entry[1], "entry_id": entry[2]}
            entry_list.append(dictionary)

        config.coordinator_stimuli.set(entry_list)
        self.master.save_config()

        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "run_coordinator.py")
        self.coordinator_process = subprocess.Popen(f"python3 {path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in self.coordinator_process.stdout:
            # self.listbox.insert(tk.END, "COORD: ".encode("UTF-8") + line)
            self.listbox.insert(tk.END, line)
            self.listbox.yview(tk.END)
        log.info("Coordinator exited")


    def disable_interface_for_coordinator(self):
        self.button_run_coordinator["state"] = tk.DISABLED
        self.button_stop_coordinator["state"] = tk.NORMAL
        self.master.notebook.tab(0, state="disabled")
        self.master.notebook.tab(1, state="disabled")
        self.master.notebook.tab(2, state="disabled")
        self.master.notebook.tab(3, state="disabled")
        for child in self.checkbox_frame.winfo_children():
            child.configure(state='disable')

    def enable_interface_after_coordinator(self):
        self.button_run_coordinator["state"] = tk.NORMAL
        self.button_stop_coordinator["state"] = tk.DISABLED
        self.master.notebook.tab(0, state="normal")
        self.master.notebook.tab(1, state="normal")
        self.master.notebook.tab(2, state="normal")
        self.master.notebook.tab(3, state="normal")
        for child in self.checkbox_frame.winfo_children():
            child.configure(state='normal')


class ListboxHandler(Handler):
    def __init__(self, box):
        self._box = box
        Handler.__init__(self)

    def emit(self, record):
        r = self.format(record) + "\n"
        self._box.insert("end", "GUI: " + r)
        self._box.yview(tk.END)
