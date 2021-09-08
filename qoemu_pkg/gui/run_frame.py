from __future__ import annotations

import logging
import shlex
import signal
import subprocess
import tkinter as tk
from tkinter import ttk
from logging import Handler, getLogger

import psutil

import qoemu_pkg.netem.netem as netem

import qoemu_pkg.gui.gui
from qoemu_pkg.coordinator import Coordinator, FINISH_CAMPAIGN_LOG, FINISH_POST_LOG
import threading
from typing import Callable, List, Optional
from subframes import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui

RUN_COORDINATOR_STR = "Run Coordinator"
STOP_COORDINATOR_STR = "Stop Coordinator"
CAMPAIGNS_STR = "Campaigns: "
POST_STR = "Post: "


class RunFrame(tk.Frame):
    def __init__(self, master, gui: Gui, get_checked_entries: Callable[[], List[str]]):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.thread = None
        self.get_checked_entries = get_checked_entries
        self.gui: Gui = gui
        self.coordinator_process: Union[subprocess.Popen, None] = None
        self.update_thread = None
        self.total_stimuli = None
        self.campaigns_finished = None
        self.post_processing_finished = None

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
        self.dropdown.pack(fill=tk.BOTH, expand=0, side="left")

        # Run Coordinator button
        self.button_run_coordinator = tk.Button(self.button_frame, text=RUN_COORDINATOR_STR,
                                                command=self.start_coordinator, width=15)
        self.button_run_coordinator.pack(fill=tk.BOTH, side="left", expand=0)

        # Stop Coordinator button
        self.button_stop_coordinator = tk.Button(self.button_frame, text=STOP_COORDINATOR_STR,
                                                 command=self.terminate_coordinator, width=15)
        self.button_stop_coordinator.pack(fill=tk.BOTH, side="left", expand=0)
        self.button_stop_coordinator["state"] = tk.DISABLED

        # Campaign progress label

        self.campaigns_finished_str = tk.StringVar(None, CAMPAIGNS_STR)
        self.campaigns_finished_label = tk.Label(master=self.button_frame,
                                                 textvariable=self.campaigns_finished_str, width=15, anchor="w")
        self.campaigns_finished_label.pack(fill=tk.BOTH, expand=0, side="left")

        # Post processing progress label
        self.post_processing_finished_str = tk.StringVar(None, POST_STR)
        self.post_label = tk.Label(master=self.button_frame,
                                   textvariable=self.post_processing_finished_str, width=10, anchor="w")
        self.post_label.pack(fill=tk.BOTH, expand=0, side="left")

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
        # for proc in self.coordinator_process.chil
        #self.coordinator_process.terminate()

        process = psutil.Process(self.coordinator_process.pid)
        for proc in process.children(recursive=True):
            proc.terminate()
        process.terminate()
        log.info("Sent SIGTERM to coordinator process. Waiting for it to terminate")
        for proc in process.children(recursive=True):
            proc.wait()
        # os.killpg(os.getpgid(self.coordinator_process.pid), signal.SIGTERM)
        self.coordinator_process.wait()
        log.info("Coordinator exited")
        netem.reset_device_and_ifb(config.net_device_name.get())
        self.enable_interface_after_coordinator()

    def start_coordinator(self):
        entries = self.get_checked_entries()
        if len(entries) < 1:
            log.info("No Parameters are selected")
            return
        self.total_stimuli = len(entries)
        self.campaigns_finished = 0
        self.post_processing_finished = 0
        self.campaigns_finished_str.set(f"{CAMPAIGNS_STR}{self.campaigns_finished}/{self.total_stimuli}")
        self.post_processing_finished_str.set(f"{POST_STR}{self.post_processing_finished}/{self.total_stimuli}")

        log.info("Starting coordinator")
        self.disable_interface_for_coordinator()

        entry_list = []
        for entry in entries:
            dictionary = {"type_id": entry[0], "table_id": entry[1], "entry_id": entry[2]}
            entry_list.append(dictionary)

        config.coordinator_stimuli.set(entry_list)
        self.master.save_config()

        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "run_coordinator.py")
        self.coordinator_process = subprocess.Popen(f"python3 {path}".split(" "), shell=False, stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
        self.update_thread = threading.Thread(target=self.display_output, daemon=True)
        self.update_thread.start()

    def display_output(self):
        for line in self.coordinator_process.stdout:
            # self.listbox.insert(tk.END, "COORD: ".encode("UTF-8") + line)
            if FINISH_CAMPAIGN_LOG.encode("UTF-8") in line:
                self.campaigns_finished += 1
                self.campaigns_finished_str.set(f"{CAMPAIGNS_STR}{self.campaigns_finished}/{self.total_stimuli}")
            if FINISH_POST_LOG.encode("UTF-8") in line:
                print("post finished")
                self.post_processing_finished += 1
                self.post_processing_finished_str.set(
                    f"{POST_STR}{self.post_processing_finished}/{self.total_stimuli}")
            self.listbox.insert(tk.END, line)
            self.listbox.yview(tk.END)

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
        self.campaigns_finished_str.set(CAMPAIGNS_STR)
        self.post_processing_finished_str.set(POST_STR)


class ListboxHandler(Handler):
    def __init__(self, box):
        self._box = box
        Handler.__init__(self)

    def emit(self, record):
        r = self.format(record) + "\n"
        self._box.insert("end", "GUI: " + r)
        self._box.yview(tk.END)
