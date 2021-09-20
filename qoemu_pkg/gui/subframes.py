from __future__ import annotations

import os.path
import tkinter as tk

import qoemu_pkg.analysis.analysis
from qoemu_pkg.gui.config import *
from tkinter import filedialog, messagebox
from qoemu_pkg.configuration import *
import logging as log
from qoemu_pkg.gui.tooltip import Tooltip
from typing import List
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui
import qoemu_pkg.gui.tooltip_strings


class StringSelectFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: Option, options: List[str], name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.options = options
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.value = tk.StringVar(self)

        initial_value = self.config_variable.get()

        if type(initial_value) == MobileDeviceType:
            initial_value = initial_value.name

        if initial_value in self.options:
            self.value.set(initial_value)
        else:
            log.debug(f"Config: '{self.name}': '{initial_value}' is not a valid option")
            self.value.set(options[0])
            self.update_config()

        self.label = tk.Label(master=self, text=f"{self.name}: ", width=30, anchor="w")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self, self.value, *self.options)
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="right")

        self.disable_log_temporarily = False
        self.value.trace_add("write", self.update_config)

    def update_config(self, *args):
        new_value = self.value.get()
        old_value = self.config_variable.get()
        if type(old_value) == MobileDeviceType:
            old_value = old_value.name
        if new_value == old_value:
            return
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        initial_value = self.config_variable.get()
        if type(initial_value) == MobileDeviceType:
            initial_value = initial_value.name
        self.disable_log_temporarily = True
        self.value.set(initial_value)
        self.disable_log_temporarily = False


class FolderFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: Option, name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.path = tk.StringVar(self)
        self.path.set(os.path.expanduser(self.config_variable.get()))

        self.button = tk.Button(self, text=f"{self.name}:", command=self.open_folder, anchor="w", width=30)
        self.button.pack(fill=tk.BOTH, side="left", expand=0)

        self.entry = tk.Entry(self, textvariable=self.path)
        self.entry.pack(fill=tk.BOTH, side="left", expand=1)
        self.entry.bind('<Leave>', self.update_config)
        self.entry.bind('<FocusOut>', self.update_config)

    def open_folder(self):
        path = filedialog.askdirectory(initialdir=self.config_variable.get())
        if len(path) > 0:
            self.path.set(path)
            self.update_config()

    def update_config(self, *args):
        if self.path.get() == self.config_variable.get():
            return
        if os.path.isdir(self.path.get()):
            self.config_variable.set(self.path.get().replace(os.path.expanduser('~'), '~', 1))
            log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")
        else:
            messagebox.showerror("Error", "Directory doesn't exist")
            self.path.set(self.config_variable.get())

    def update_display(self):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.config_variable.get())


class FileFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: Option, name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.path = tk.StringVar(self)
        self.path.set(os.path.expanduser(self.config_variable.get()))

        self.button = tk.Button(self, text=f"{self.name}:", command=self.open_file, anchor="w", width=30)
        self.button.pack(fill=tk.BOTH, side="left", expand=0)

        self.entry = tk.Entry(self, textvariable=self.path)
        self.entry.pack(fill=tk.BOTH, side="left", expand=1)

    def open_file(self):
        path = filedialog.askopenfilename()
        if len(path) > 0:
            self.path.set(path)
            self.update_config()

    def update_config(self, *args):
        if self.path.get() == self.config_variable.get():
            return
        if os.path.isfile(self.path.get()):
            self.config_variable.set(self.path.get().replace(os.path.expanduser('~'), '~', 1))
            log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")
        else:
            messagebox.showerror("Error", "File doesn't exist")
            self.path.set(self.config_variable.get())

    def update_display(self):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.config_variable.get())


class BooleanFrame(tk.Frame):

    def __init__(self, master, gui: Gui, config_variable: BoolOption, name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.value = tk.BooleanVar(self)
        self.value.set(self.config_variable.get())

        self.label = tk.Label(master=self, text=self.name + ": ", width=30, anchor="w")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.set_false = tk.Radiobutton(self, text="False", variable=self.value,
                                        value=False)
        self.set_false.pack(fill=tk.BOTH, expand=1, side="right")
        self.set_true = tk.Radiobutton(self, text="True", variable=self.value,
                                       value=True)
        self.set_true.pack(fill=tk.BOTH, expand=1, side="right")

        self.value.trace_add("write", self.update_config)

    def update_config(self, *args):
        if self.config_variable.get() == self.value.get():
            return
        self.config_variable.set(self.value.get())
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        if self.config_variable.get():
            self.value.set(True)
        else:
            self.value.set(False)


class StringFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: Option, name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.label = tk.Label(master=self, text=f"{self.name}:  ", width=30, anchor="w")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self)
        self.input.insert(0, self.config_variable.get())
        self.input.pack(fill=tk.BOTH, expand=1, side="left")
        self.input.bind('<Leave>', self.update_config)
        self.input.bind('<FocusOut>', self.update_config)

    def update_config(self, *args):
        new_value = self.input.get()

        if new_value == self.config_variable.get():
            return

        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.input.delete(0, tk.END)
        self.input.insert(0, self.config_variable.get())


class IntegerFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: IntOption, name: str = None, min_value: int = None,
                 max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.label = tk.Label(master=self, text=f"{self.name}:", width=45, anchor="w")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self, width=10)
        self.input.insert(0, self.config_variable.get())
        self.input.pack(fill=tk.BOTH, expand=0, side="left")
        self.input.bind('<Leave>', self.update_config)
        self.input.bind('<FocusOut>', self.update_config)

    def update_config(self, *args):
        try:
            new_value = int(self.input.get())
        except ValueError:
            messagebox.showerror("Error", "Not an Integer")
            self.input.delete(0, tk.END)
            self.input.insert(0, self.config_variable.get())
            return

        if new_value == self.config_variable.get():
            return

        if self.min_value is not None:
            if new_value < self.min_value:
                messagebox.showerror("Error", "Value too small")
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        if self.max_value is not None:
            if new_value > self.max_value:
                messagebox.showerror("Error", "Value too large")
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        self.config_variable.set(new_value)
        self.update_display()
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.input.delete(0, tk.END)
        self.input.insert(0, self.config_variable.get())


class FloatFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: FloatOption, name: str = None, min_value: float = None,
                 max_value: float = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.label = tk.Label(master=self, text=f"{self.name}:", width=45, anchor="w")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self, width=10)
        self.input.insert(0, self.config_variable.get())
        self.input.pack(fill=tk.BOTH, expand=0, side="left")
        self.input.bind('<Leave>', self.update_config)
        self.input.bind('<FocusOut>', self.update_config)

    def update_config(self, *args):
        try:
            new_value = float(self.input.get())
        except ValueError:
            messagebox.showerror("Error", "Not a Float")
            self.input.delete(0, tk.END)
            self.input.insert(0, self.config_variable.get())
            return

        if new_value == self.config_variable.get():
            return

        if self.min_value is not None:
            if new_value < self.min_value:
                messagebox.showerror("Error", "Value too small")
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        if self.max_value is not None:
            if new_value > self.max_value:
                messagebox.showerror("Error", "Value too large")
                self.input.delete(0, tk.END)
                self.input.insert(0, self.config_variable.get())
                return

        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.input.delete(0, tk.END)
        self.input.insert(0, str(self.config_variable.get()))


class ListIntegerFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: ListIntOption, name: str = None, value_name: str = "Value",
                 min_value: int = None, max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.value_name = value_name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        scrollbar = tk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.label = tk.Label(master=self, text=f"{self.name}: ", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add = tk.Button(self.button_frame, text=f"Add {self.value_name}",
                                    command=self.add_value)
        self.button_add.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete = tk.Button(self.button_frame, text=f"Delete {self.value_name}",
                                       command=self.delete_value)
        self.button_delete.pack(fill=tk.BOTH, side="top", expand=0)

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

        self.update_config()

    def add_value(self):
        try:
            value = int(self.input.get())
        except ValueError:
            self.input.delete(0, "end")
            messagebox.showerror("Error", "Not an Integer")
            return

        if self.min_value is not None:
            if value < self.min_value:
                self.input.delete(0, "end")
                messagebox.showerror("Error", "Value too small")
                return

        if self.max_value:
            if value > self.max_value:
                self.input.delete(0, "end")
                messagebox.showerror("Error", "Value too large")
                return

        if value not in self.listbox.get(0, "end"):
            self.listbox.insert('end', value)
            self.sort_values()
            self.config_variable.set([int(element) for element in self.listbox.get(0, tk.END)])

        self.input.delete(0, "end")

    def sort_values(self):
        values = []
        for entry in self.listbox.get(0, "end"):
            values.append(int(entry))
            self.listbox.delete(0)
        values.sort()
        for entry in values:
            self.listbox.insert("end", entry)

    def update_config(self):
        new_value = [int(element) for element in self.listbox.get(0, tk.END)]
        if self.config_variable.get() == new_value:
            return
        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.listbox.delete(0, tk.END)
        for integer in self.config_variable.get():
            self.listbox.insert(0, str(integer))
        self.sort_values()


class ListFloatFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: ListFloatOption, name: str = None, value_name: str = "Value",
                 min_value: int = None, max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.value_name = value_name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        scrollbar = tk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.label = tk.Label(master=self, text=f"{self.name}: ", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add = tk.Button(self.button_frame, text=f"Add {self.value_name}",
                                    command=self.add_value)
        self.button_add.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete = tk.Button(self.button_frame, text=f"Delete {self.value_name}",
                                       command=self.delete_value)
        self.button_delete.pack(fill=tk.BOTH, side="top", expand=0)

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

        self.update_config()

    def add_value(self):
        try:
            value = float(self.input.get())
        except ValueError:
            self.input.delete(0, "end")
            return

        if self.min_value is not None:
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
            self.config_variable.set([float(element) for element in self.listbox.get(0, tk.END)])

        self.input.delete(0, "end")

    def sort_values(self):
        values = []
        for entry in self.listbox.get(0, "end"):
            values.append(float(entry))
            self.listbox.delete(0)
        values.sort()
        for entry in values:
            self.listbox.insert("end", entry)

    def update_config(self):
        new_value = [float(element) for element in self.listbox.get(0, tk.END)]
        if self.config_variable.get() == new_value:
            return
        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.listbox.delete(0, tk.END)
        for value in self.config_variable.get():
            self.listbox.insert(0, float(value))
        self.sort_values()


class AudioStartStopFrame(tk.Frame):

    def __init__(self, master, gui: Gui, config_variable: ListFloatOption, name: str = None, value_name: str = "Value Pair",
                 min_value: int = None, max_value: int = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.value_name = value_name
        self.min_value = min_value
        self.max_value = max_value
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        scrollbar = tk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.label = tk.Label(master=self, text=f"{self.name}: ", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input_label_frame = tk.Frame(self.button_frame, background="#DCDCDC", bd=1, relief="sunken")
        self.input_label_frame.pack(fill=tk.BOTH, expand=0, side="top")

        self.label_start = tk.Label(master=self.input_label_frame, text=f"Start: ", width=10)
        self.label_start.pack(fill=tk.BOTH, expand=0, side="left")

        self.label_stop = tk.Label(master=self.input_label_frame, text=f"Stop: ", width=10)
        self.label_stop.pack(fill=tk.BOTH, expand=0, side="left")

        self.input_frame = tk.Frame(self.button_frame, background="#DCDCDC", bd=1, relief="sunken")
        self.input_frame.pack(fill=tk.BOTH, expand=0, side="top")

        self.input = tk.Entry(self.input_frame, width=10)
        self.input.pack(fill=tk.BOTH, expand=0, side="left")

        self.input2 = tk.Entry(self.input_frame, width=10)
        self.input2.pack(fill=tk.BOTH, expand=0, side="left")

        self.button_add = tk.Button(self.button_frame, text=f"Add {self.value_name}",
                                    command=self.add_value)
        self.button_add.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete = tk.Button(self.button_frame, text=f"Delete {self.value_name}",
                                       command=self.delete_value)
        self.button_delete.pack(fill=tk.BOTH, side="top", expand=0)

        self.initial_values = tk.StringVar()
        self.initial_values.set(self.config_variable.get())

        self.listbox = tk.Listbox(self, listvariable=self.initial_values, height=1)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")

        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)

    def delete_value(self):
        try:
            index = self.listbox.curselection()[0]
            self.listbox.delete(index)
            self.listbox.delete(index - index % 2)
        except tk.TclError:
            pass

        self.update_config()

    def add_value(self):
        try:
            value = float(self.input.get())
            value2 = float(self.input2.get())
        except ValueError:
            messagebox.showerror("Error", "Not a Float")
            self.input.delete(0, "end")
            self.input2.delete(0, "end")
            return

        if value >= value2:
            messagebox.showerror("Error", "Start value larger than stop value")
            self.input.delete(0, "end")
            self.input2.delete(0, "end")
            return

        if self.min_value is not None:
            if value < self.min_value or value2 < self.min_value:
                messagebox.showerror("Error", "Value too small")
                self.input.delete(0, "end")
                self.input2.delete(0, "end")
                return

        if self.max_value:
            if value > self.max_value or value2 > self.max_value:
                messagebox.showerror("Error", "Value too large")
                self.input.delete(0, "end")
                self.input2.delete(0, "end")
                return

        if value in self.listbox.get(0, "end") or value2 in self.listbox.get(0, "end"):
            messagebox.showerror("Error", "Value exists already")
            self.input.delete(0, "end")
            self.input2.delete(0, "end")
            return

        traversed = 0
        start = False
        last_value = -1
        for current_value in [float(v) for v in self.listbox.get(0, "end")]:
            if start is True and value2 > last_value:
                messagebox.showerror("Error", "Value pair overlaps with existing pair")
                self.input.delete(0, "end")
                self.input2.delete(0, "end")
                return

            if last_value < value < current_value:
                if traversed % 2 == 1:
                    messagebox.showerror("Error", "Value pair overlaps with existing pair")
                    self.input.delete(0, "end")
                    self.input2.delete(0, "end")
                    return
                start = True
            last_value = current_value
            traversed += 1


        self.listbox.insert('end', value)
        self.listbox.insert('end', value2)
        self.sort_values()
        self.update_config()
        self.input.delete(0, "end")
        self.input2.delete(0, "end")

    def sort_values(self):
        values = []
        for entry in self.listbox.get(0, "end"):
            values.append(float(entry))
            self.listbox.delete(0)
        values.sort()
        for entry in values:
            self.listbox.insert("end", entry)

    def update_config(self):
        new_value = [float(element) for element in self.listbox.get(0, tk.END)]
        if self.config_variable.get() == new_value:
            return
        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        self.listbox.delete(0, tk.END)
        for value in self.config_variable.get():
            self.listbox.insert(0, float(value))
        self.sort_values()


class CheckboxToListFrame(tk.Frame):

    def __init__(self, master, gui: Gui, config_variable: ListOption, value_names: List[str], name: str = None):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.value_names = value_names
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.label = tk.Label(master=self, text=f"{self.name}: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.checkbox_variable_tuples = []

        for value_name in value_names:
            variable = tk.IntVar()
            checkbox = tk.Checkbutton(self, text=value_name, variable=variable, command=self.update_config)
            self.checkbox_variable_tuples.append((checkbox, variable))

        for checkbox, variable in self.checkbox_variable_tuples:
            checkbox.pack(fill=tk.BOTH, expand=1, side="left")
            if checkbox["text"] in self.config_variable.get():
                checkbox.select()

    def update_config(self):
        result = []
        for checkbox, var in self.checkbox_variable_tuples:
            if var.get() == 1:
                result.append(checkbox["text"])
        if self.config_variable.get() == result:
            return
        self.config_variable.set(result)
        log.debug(f"Config: '{self.name}' set to: {self.config_variable.get()}")

    def update_display(self):
        for checkbox, variable in self.checkbox_variable_tuples:
            if checkbox["text"] in self.config_variable.get():
                checkbox.select()
            else:
                checkbox.deselect()


class CheckboxToBooleanFrame(tk.Frame):

    def __init__(self, master, gui: Gui, config_variables: List[BoolOption], name: str, variable_names: List[str]):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variables = config_variables
        self.name = name
        self.variable_names = variable_names
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.label = tk.Label(master=self, text=f"{self.name}: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.tuples = []

        for i, config_variable in enumerate(config_variables):
            var = tk.IntVar()
            checkbox = tk.Checkbutton(self, text=self.variable_names[i], variable=var, command=self.update_config)
            tooltip = Tooltip(checkbox, text=config_variable.tooltip)
            self.tuples.append((config_variable, checkbox, var))

            checkbox.pack(fill=tk.BOTH, expand=1, side="left")
            if config_variable.get():
                checkbox.select()

    def update_config(self):

        for config_variable, checkbox, var in self.tuples:
            if bool(var.get()) != config_variable.get():
                config_variable.set(bool(var.get()))
                log.debug(f"Config: '{checkbox['text']}' set to: {config_variable.get()}")

    def update_display(self):
        for config_variable, checkbox, var in self.tuples:
            if config_variable.get():
                checkbox.select()
            else:
                checkbox.deselect()


class PlotsFrame(tk.Frame):
    def __init__(self, master, gui: Gui, config_variable: ListOption, name: str = None, value_name: str = "Value"):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.config_variable = config_variable
        if name:
            self.name = name
        else:
            self.name = self.config_variable.option
        self.value_name = value_name
        self.tooltip = Tooltip(self, text=self.config_variable.tooltip)
        self.gui: Gui = gui
        self.gui.updatable_elements.append(self)

        self.list_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.list_frame.pack(fill=tk.BOTH, expand=0, side="top")

        self.label = tk.Label(master=self.list_frame, text=f"{self.name}: ", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_frame = tk.Frame(self.list_frame, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.button_add = tk.Button(self.button_frame, text=f"Add {self.value_name}",
                                    command=self.add_value)
        self.button_add.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete = tk.Button(self.button_frame, text=f"Delete {self.value_name}",
                                       command=self.delete_value)
        self.button_delete.pack(fill=tk.BOTH, side="top", expand=0)

        self.initial_values = tk.StringVar()
        self.initial_values.set(self.config_variable.get())

        self.listbox = tk.Listbox(self.list_frame, listvariable=self.initial_values, height=5)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="left")
        scrollbar = tk.Scrollbar(self.list_frame, orient="vertical")
        scrollbar.pack(side="left", fill="y")

        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.directions_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.directions_frame.pack(fill=tk.BOTH, expand=0, side="top")
        label = tk.Label(master=self.directions_frame, text=f"Directions: ", width=20, anchor="w")
        label.pack(fill=tk.BOTH, expand=0, side="left")
        self.direction_tuples = []
        for direction in qoemu_pkg.analysis.analysis.DIRECTIONS:
            variable = tk.IntVar()
            checkbox = tk.Checkbutton(self.directions_frame, text=direction, variable=variable, width=10, anchor="w")
            self.direction_tuples.append((checkbox, variable))
            checkbox.pack(fill=tk.BOTH, expand=0, side="left")
            if direction == qoemu_pkg.analysis.analysis.IN:
                checkbox.select()

        self.protocols_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.protocols_frame.pack(fill=tk.BOTH, expand=0, side="top")
        label = tk.Label(master=self.protocols_frame, text=f"Protocols: ", width=20, anchor="w")
        label.pack(fill=tk.BOTH, expand=0, side="left")
        self.protocol_tuples = []
        for protocol in qoemu_pkg.analysis.analysis.PROTOCOLS:
            variable = tk.IntVar()
            checkbox = tk.Checkbutton(self.protocols_frame, text=protocol, variable=variable, width=10, anchor="w")
            self.protocol_tuples.append((checkbox, variable))
            checkbox.pack(fill=tk.BOTH, expand=0, side="left")
            if protocol == qoemu_pkg.analysis.analysis.ALL:
                checkbox.select()

        self.kinds_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.kinds_frame.pack(fill=tk.BOTH, expand=0, side="top")
        label = tk.Label(master=self.kinds_frame, text=f"Kind: ", width=20, anchor="w")
        label.pack(fill=tk.BOTH, expand=0, side="left")
        self.kinds_variable = tk.StringVar()
        for i, kind in enumerate(qoemu_pkg.analysis.analysis.KINDS):
            checkbox = tk.Radiobutton(self.kinds_frame, text=kind, variable=self.kinds_variable, value=kind, width=9,
                                      anchor="w")
            checkbox.pack(fill=tk.BOTH, expand=0, side="left")
            if i == 0:
                checkbox.select()

    def delete_value(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

        self.update_config()

    def add_value(self):
        result = {"directions": [], "protocols": [], "kind": []}
        for checkbox, var in self.direction_tuples:
            if var.get() == 1:
                result["directions"].append(checkbox["text"])
        for checkbox, var in self.protocol_tuples:
            if var.get() == 1:
                result["protocols"].append(checkbox["text"])
        result["kind"].append(self.kinds_variable.get())

        if all([len(entry) > 0 for entry in result.values()]):
            self.listbox.insert('end', result)
        else:
            messagebox.showinfo("Information", "Must select at least one direction and protocol")
            return
        if str(result) in self.listbox.get(0, "end"):
            messagebox.showinfo("Information", "Selection already in list")
            return

        self.update_config()

    def update_config(self):
        new_value = [element for element in self.listbox.get(0, tk.END)]
        if self.config_variable.get() == new_value:
            return
        self.config_variable.set(new_value)
        log.debug(f"Config: '{self.name}' modified")

    def update_display(self):
        self.listbox.delete(0, tk.END)
        for dictionary in self.config_variable.get():
            self.listbox.insert(0, str(dictionary))
