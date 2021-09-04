import tkinter as tk
from config import *
from tkinter import filedialog
from qoemu_pkg.configuration import *
import logging as log
from tooltip import Tooltip
from typing import List
import tooltip_strings


class StringSelectFrame(tk.Frame):
    def __init__(self, master, config_variable: Option, name: str, options: List[str]):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.options = options
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.value = tk.StringVar(self)

        initial_value = self.config_variable.get()

        if type(initial_value) == MobileDeviceType:
            initial_value = initial_value.name

        if initial_value in self.options:
            self.value.set(initial_value)
        else:
            self.value.set(options[0])
            self._update_config()

        self.label = tk.Label(master=self, text=f"{self.name}: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self, self.value, *self.options)
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="right")

        self.value.trace_add("write", self._update_config)

    def _update_config(self, *args):
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class FolderFrame(tk.Frame):
    def __init__(self, master, config_variable: Option, name: str):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.path = tk.StringVar(self)
        self.path.set(os.path.expanduser(self.config_variable.get()))

        self.button = tk.Button(self, text=f"Set {self.name}: ", command=self.open_folder)
        self.button.pack(fill=tk.BOTH, side="top", expand=1)

        self.entry = tk.Entry(self, textvariable=self.path)
        self.entry.pack(fill=tk.BOTH, side="top", expand=1)

    def open_folder(self):
        self.path.set(filedialog.askdirectory())
        self.config_variable.set(self.path.get().replace(os.path.expanduser('~'), '~', 1))
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class BooleanFrame(tk.Frame):

    def __init__(self, master, config_variable: BoolOption, name: str):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.value = tk.BooleanVar(self)
        self.value.set(self.config_variable.get())

        self.label = tk.Label(master=self, text=self.name + ": ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.set_false = tk.Radiobutton(self, text="False", variable=self.value,
                                        value=False)
        self.set_false.pack(fill=tk.BOTH, expand=1, side="right")
        self.set_true = tk.Radiobutton(self, text="True", variable=self.value,
                                       value=True)
        self.set_true.pack(fill=tk.BOTH, expand=1, side="right")

        self.value.trace_add("write", self._update_config)

    def _update_config(self, *args):
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class StringFrame(tk.Frame):
    def __init__(self, master, config_variable: Option, name: str):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.value = tk.StringVar(self)
        self.value.set(self.config_variable.get())

        self.label = tk.Label(master=self, text=f"{self.name}:  ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.label_value = tk.Label(master=self, textvariable=self.value, width=40)
        self.label_value.pack(fill=tk.BOTH, expand=0, side="left")

        self.button = tk.Button(self, text="Set", command=self._update_config)
        self.button.pack(side="left", expand=0, padx=10, pady=1)

        self.input = tk.Entry(self)
        self.input.insert(0, self.value.get())
        self.input.pack(fill=tk.BOTH, expand=1, side="left")

    def _update_config(self, *args):
        self.value.set(self.input.get())
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class IntegerFrame(tk.Frame):
    def __init__(self, master, config_variable: Option, name: str, min_value: int = None, max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.value = tk.IntVar(self)
        self.value.set(self.config_variable.get())

        self.label = tk.Label(master=self, text=f"{self.name}:  ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.label_value = tk.Label(master=self, textvariable=self.value, width=20)
        self.label_value.pack(fill=tk.BOTH, expand=0, side="left")

        self.button = tk.Button(self, text="Set", command=self._update_config)
        self.button.pack(side="left", expand=0, padx=40, pady=1)

        self.input = tk.Entry(self)
        self.input.insert(0, self.value.get())
        self.input.pack(fill=tk.BOTH, expand=1, side="right")

    def _update_config(self, *args):
        try:
            new_value = int(self.input.get())
        except ValueError:
            self.input.delete(0, tk.END)
            self.input.insert(0, self.config_variable.get())
            return

        if new_value == self.config_variable.get():
            return

        if self.min_value is not None:
            if new_value < self.min_value:
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        if self.max_value is not None:
            if new_value > self.max_value:
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        self.value.set(new_value)
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class FloatFrame(tk.Frame):
    def __init__(self, master, config_variable: Option, name: str, min_value: float = None, max_value: float = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.value = tk.StringVar(self)
        self.value.set(self.config_variable.get())

        self.label = tk.Label(master=self, text=f"{self.name}:  ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.label_value = tk.Label(master=self, textvariable=self.value, width=20)
        self.label_value.pack(fill=tk.BOTH, expand=0, side="left")

        self.button = tk.Button(self, text="Set", command=self._update_config)
        self.button.pack(side="left", expand=0, padx=40, pady=1)

        self.input = tk.Entry(self)
        self.input.insert(0, self.value.get())
        self.input.pack(fill=tk.BOTH, expand=1, side="right")

    def _update_config(self, *args):
        try:
            new_value = float(self.input.get())
        except ValueError:
            self.input.delete(0, tk.END)
            self.input.insert(0, self.config_variable.get())
            return

        if new_value == self.config_variable.get():
            return

        if self.min_value is not None:
            if new_value < self.min_value:
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        if self.max_value is not None:
            if new_value > self.max_value:
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        self.value.set(str(new_value))
        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class IntegerListFrame(tk.Frame):
    def __init__(self, master, config_variable: ListIntOption, name: str, value_name: str,
                 min_value: int = None, max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.value_name = value_name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        scrollbar = tk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.label = tk.Label(master=self, text=f"{self.name}: ", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add_port = tk.Button(self.button_frame, text=f"Add {self.value_name}",
                                         command=self.add_value)
        self.button_add_port.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete_port = tk.Button(self.button_frame, text=f"Delete {self.value_name}",
                                            command=self.delete_value)
        self.button_delete_port.pack(fill=tk.BOTH, side="top", expand=0)

        self.initial_values = tk.StringVar()
        self.initial_values.set(self.config_variable.get())

        self.listbox = tk.Listbox(self, listvariable=self.initial_values, height=1)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="top")

        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)

    def delete_value(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

        self._update_config()

    def add_value(self):
        try:
            value = int(self.input.get())
        except ValueError:
            self.input.delete(0, "end")
            return

        if self.min_value:
            if value < self.min_value:
                self.input.delete(0, "end")
                return

        if self.max_value:
            if value > self.max_value:
                self.input.delete(0, "end")
                return

        if value not in self.listbox.get(0, "end"):
            self.listbox.insert('end', value)
            self.sort_values()
            self._update_config()

        self.input.delete(0, "end")

    def sort_values(self):
        values = []
        for entry in self.listbox.get(0, "end"):
            values.append(entry)
            self.listbox.delete(0)
        values.sort()
        for entry in values:
            self.listbox.insert("end", entry)

    def _update_config(self):
        self.config_variable.set([int(element) for element in self.listbox.get(0, tk.END)])
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")


class CheckboxFrame(tk.Frame):

    def __init__(self, master, config_variable: ListOption, name: str, value_names: List[str]):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        self.name = name
        self.value_names = value_names
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)

        self.label = tk.Label(master=self, text=f"{self.name}: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.checkboxes_vars = []

        for value_name in value_names:
            var = tk.IntVar()
            checkbox = tk.Checkbutton(self, text=value_name, variable=var, command=self._update_config)
            self.checkboxes_vars.append((checkbox, var))

        for checkbox, var in self.checkboxes_vars:
            checkbox.pack(fill=tk.BOTH, expand=1, side="left")
            if checkbox["text"] in self.config_variable.get():
                checkbox.select()

    def _update_config(self):
        result = []
        for checkbox, var in self.checkboxes_vars:
            if var.get() == 1:
                result.append(checkbox["text"])
        self.config_variable.set(result)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")
