# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#           Jan Andreas Krahl <krahl.jan@hm.edu>
#
# License:  LGPL 3.0 - see LICENSE file for details
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from ttkwidgets import CheckboxTreeview
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from qoeval_pkg.configuration import QoEvalConfiguration
import qoeval_pkg
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoeval_pkg.gui.gui import Gui

from qoeval_pkg.parser import parser

OPEN_FILE_TEXT = "Open Parameter File"
PARAMETER_FILE_DESC = "Parameter File:"


class ParameterFrame(tk.Frame):

    def __init__(self, master, gui: Gui):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.gui: Gui = gui

        self.gui.updatable_elements.append(self)

        # buttons
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=False)

        self.button_open_file = tk.Button(self.button_frame, text=OPEN_FILE_TEXT, command=self.open_file_with_asking,
                                          width=15)

        self.button_open_file.pack(fill=tk.BOTH, side="left", expand=0)

        self.parameter_file = tk.StringVar(value=self.gui.qoeval_config.parameter_file.get())
        self.parameter_file_label = tk.Label(master=self.button_frame, textvariable=self.parameter_file,
                                             anchor="c")
        self.parameter_file_label.pack(fill=tk.BOTH, expand=1, side="left")

        # treeview in a frame with vertical scrollbar

        self.tree_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.tree_frame.pack(fill=tk.BOTH, expand=True, side="top")

        self.test = ttk.Treeview()
        self.tree = FasterScrollCheckboxTreeview(self.tree_frame)
        self.tree.pack(expand=True, fill=tk.BOTH, side="right")

        # treeview scrollbars

        tree_scroll_v = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_v.set)
        tree_scroll_v.pack(fill=tk.BOTH, side="left")

        tree_scroll_h = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_scroll_h.set)
        tree_scroll_h.pack(fill=tk.BOTH, side="bottom")

        # treeview column config

        self.tree['columns'] = qoeval_pkg.parser.parser.PARAMETER_NAMES
        self.tree.column("#0", stretch=False, minwidth=80, width=120)
        for column in self.tree['columns']:
            self.tree.heading(column, text=column)
            if column == "link":
                self.tree.column(column, stretch=False, minwidth=120, width=400, anchor="e")
            elif column in ['t_init', 'rul', 'rdl', 'dul', 'ddl', 'codec']:
                self.tree.column(column, stretch=False, minwidth=60, width=60, anchor="e")
            else:
                self.tree.column(column, stretch=False, minwidth=60, width=100, anchor="e")

        # update config
        self.tree.bind('<<TreeviewSelect>>', self.update_config)

        self.open_file(self.gui.qoeval_config.parameter_file.get(), path_from_config=True)

    def update_config(self, *args):
        """Update the config with the currently selected entries"""
        entries = self.get_checked_entries()
        entry_list = []
        for entry in entries:
            dictionary = {"type_id": entry[0], "table_id": entry[1], "entry_id": entry[2]}
            entry_list.append(dictionary)

        self.gui.qoeval_config.gui_coordinator_stimuli.set(entry_list)

    def open_file_with_asking(self):
        """Open a file dialog and open selected file"""
        path = askopenfilename()
        if len(path) > 0:
            self.gui.qoeval_config.gui_coordinator_stimuli.set([])
            self.open_file(path)

    def open_file(self, filename, path_from_config=False):
        """Open a file and update the treeview"""
        try:
            parser.load_parameter_file(filename)
        except FileNotFoundError:
            self.gui.qoeval_config.parameter_file.set(self.parameter_file.get())
            if path_from_config:
                messagebox.showerror(f"Error", f"Parameter file \"{filename}\" specified "
                                               f"in selected config file not found")
            else:
                messagebox.showerror(f"Error", f"Parameter file \"{filename}\" not found")
            return

        if filename != self.gui.qoeval_config.parameter_file.get():
            self.gui.qoeval_config.parameter_file.set(filename)
            self.parameter_file.set(filename)

        for i in self.tree.get_children():
            self.tree.delete(i)

        for i, type_id in enumerate(parser.get_type_ids()):
            try:  # in case the entry already exists we get a tk.TclError
                self.tree.insert(parent="", index=i, text=type_id, iid=type_id)
            except tk.TclError:
                pass
            for j, table_id in enumerate(parser.get_table_ids(type_id)):
                try:  # in case the entry already exists we get a tk.TclError
                    self.tree.insert(parent=type_id, index=j, text=table_id, iid=f"{type_id}:{table_id}")
                except tk.TclError:
                    pass
                for k in parser.get_entry_ids(type_id, table_id):
                    data = list(parser.get_parameters(type_id, table_id, k).values())
                    data.extend([parser.get_link(type_id, table_id, k),
                                 parser.get_start(type_id, table_id, k),
                                 parser.get_end(type_id, table_id, k)])
                    try:  # in case the entry already exists we get a tk.TclError
                        self.tree.insert(parent=f"{type_id}:{table_id}", text=k, index=k,
                                         iid=f"{type_id}:{table_id}:{k}",
                                         values=data)
                        if dict(type_id=type_id, table_id=table_id, entry_id=k) in \
                                self.gui.qoeval_config.gui_coordinator_stimuli.get():
                            self.tree.item(f"{type_id}:{table_id}:{k}", tags=['checked'])
                    except tk.TclError:
                        pass

                checked_list = ['checked' in self.tree.item(child)['tags'] for child in
                                self.tree.get_children(f"{type_id}:{table_id}")]
                if all(checked_list):
                    self.tree.item(f"{type_id}:{table_id}", tags=['checked'])
                elif any(checked_list):
                    self.tree.item(f"{type_id}:{table_id}", tags=['tristate'], open=True)

            checked_list = ['checked' in self.tree.item(child)['tags'] for child in
                            self.tree.get_children(f"{type_id}")]
            checked_tristate_list = [
                ('tristate' in self.tree.item(child)['tags'] or 'checked' in self.tree.item(child)['tags']) for child in
                self.tree.get_children(f"{type_id}")]
            if any(checked_tristate_list):
                self.tree.item(f"{type_id}", tags=['tristate'], open=True)
            if all(checked_list):
                self.tree.item(f"{type_id}", tags=['checked'])

        self.parameter_file.set(self.gui.qoeval_config.parameter_file.get())
        return

    def get_checked_entries(self):
        """Returns a list of all checked entries"""
        result = []
        for entry in self.tree.get_checked():
            result.append(entry.split(":"))
        return result

    def update_display(self, update=True):
        """Update the frame to represent the currently loaded config file"""
        self.open_file(self.gui.qoeval_config.parameter_file.get())


class FasterScrollCheckboxTreeview(CheckboxTreeview):
    """A Checkbox Treeview that allows for faster scrollspeed
    Source: https://stackoverflow.com/questions/46226070/python-3-tkinter-x-scroll-using-arrow-very-slow
    """
    def __init__(self, parent, **kwargs):
        CheckboxTreeview.__init__(self, parent, **kwargs)
        self.vanilla_xview = tk.XView.xview

    def xview(self, *args):
        #   here's our multiplier
        multiplier = 100

        if 'units' in args:
            #   units in args - user clicked the arrows
            #   time to build a new args with desired increment
            mock_args = args[:1] + (str(multiplier * int(args[1])),) + args[2:]
            return self.vanilla_xview(self, *mock_args)
        else:
            #   just do default things
            return self.vanilla_xview(self, *args)
