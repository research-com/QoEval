import tkinter as tk
from ttkwidgets import CheckboxTreeview
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename

from qoemu_pkg.parser import parser


class ParameterFrame(tk.Frame):

    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master

        # buttons
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=False)

        self.button_open_file = tk.Button(self.button_frame, text="Open File", command=self.open_file)

        self.button_open_file.pack(fill=tk.BOTH, side="left", expand=1)

        self.button_create_entry = tk.Button(self.button_frame, text="Create Custom Entry",
                                             command=self.custom_entry_window)
        self.button_create_entry.pack(expand=1, fill=tk.BOTH, side="left")

        self.button_save_selected = tk.Button(self.button_frame, text="Save Selected",
                                              command=self.save_selected_entries)
        self.button_save_selected.pack(expand=1, fill=tk.BOTH, side="left")

        self.button_delete_selected = tk.Button(self.button_frame, text="Delete Selected",
                                                command=self.delete_selected_entries)
        self.button_delete_selected.pack(expand=1, fill=tk.BOTH, side="left")

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

        self.tree['columns'] = ('t_init', 'rul', 'rdl', 'dul', 'ddl', 'link', 'start', 'end', 'codec')
        self.tree.column("#0", width=30, stretch=True, minwidth=150)
        for column in self.tree['columns']:
            self.tree.heading(column, text=column)
            if column == "link":
                self.tree.column(column, width=190, stretch=True, minwidth=250)
            else:
                self.tree.column(column, width=30, stretch=True, minwidth=80)

        # make leftclick copy possible in treeview
        self.tree.bind('<ButtonRelease-1>', self._tree_copy_click_handler)
        # end

    def open_file(self):
        filename = askopenfilename()

        try:
            parser.load_parameter_file(filename, False)
        except:
            return None

        try:  # in case the entry already exists we get a tk.TclError
            self.tree.insert(parent="", index=0, text=filename, iid=filename)
        except tk.TclError:
            pass

        for i, type_id in enumerate(parser.get_type_ids()):
            try:  # in case the entry already exists we get a tk.TclError
                self.tree.insert(parent=filename, index=i, text=type_id, iid=type_id)
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
                                 parser.get_end(type_id, table_id, k),
                                 parser.get_codec(type_id, table_id, k)])
                    try:  # in case the entry already exists we get a tk.TclError
                        self.tree.insert(parent=f"{type_id}:{table_id}", text=k, index=k,
                                         iid=f"{type_id}:{table_id}:{k}",
                                         values=data)
                    except tk.TclError:
                        pass

    def _tree_copy_click_handler(self, event):
        """
            Allows copying from treeview with left click
        """
        try:
            cur_item = self.tree.item(self.tree.focus())
            col = self.tree.identify_column(event.x)
            if col in ["#1", "#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9"]:
                self.master.clipboard_clear()
                self.master.clipboard_append(cur_item['values'][int(col[1]) - 1])
        except IndexError:
            pass

    def print_checked(self):
        for entry in self.master.tree.get_checked():
            print(entry)

    def save_selected_entries(self):
        pass

    def delete_selected_entries(self):
        for i in range(0, 5):
            for entry in self.tree.get_checked():
                self.tree.delete(entry)

    def create_entry(self, name, type_id, table_id, entry_id, data):
        try:  # in case the entry already exists we get a tk.TclError
            self.tree.insert(parent="", index=0, text=name, iid=name)
        except tk.TclError:
            pass
        try:  # in case the entry already exists we get a tk.TclError
            self.tree.insert(parent=name, index=0, text=type_id, iid=type_id)
        except tk.TclError:
            pass
        try:  # in case the entry already exists we get a tk.TclError
            self.tree.insert(parent=type_id, index=0, text=table_id, iid=f"{type_id}:{table_id}")
        except tk.TclError:
            pass
        try:  # in case the entry already exists we get a tk.TclError
            self.tree.insert(parent=f"{type_id}:{table_id}", text=entry_id, index=entry_id,
                             iid=f"{type_id}:{table_id}:{entry_id}",
                             values=data)
        except tk.TclError:
            pass

    def custom_entry_window(self):
        # Toplevel object which will
        # be treated as a new window
        window = tk.Toplevel(self.master)

        type_id = tk.StringVar(self)

        t_init_label = tk.Label(master=window, text="t_init", relief="flat")
        t_init_label.grid(row=0, column=1, sticky="nswe")
        t_init = tk.Entry(window)
        t_init.grid(row=1, column=1, sticky="nswe")

        rul_label = tk.Label(master=window, text="rul", relief="flat", width=12)
        rul_label.grid(row=0, column=2, sticky="nswe")
        rul = tk.Entry(window)
        rul.grid(row=1, column=2, sticky="nswe")

        rdl_label = tk.Label(master=window, text="rdl", relief="flat", width=12)
        rdl_label.grid(row=0, column=3, sticky="nswe")
        rdl = tk.Entry(window)
        rdl.grid(row=1, column=3, sticky="nswe")

        dul_label = tk.Label(master=window, text="dul", relief="flat", width=12)
        dul_label.grid(row=0, column=4, sticky="nswe")
        dul = tk.Entry(window)
        dul.grid(row=1, column=4, sticky="nswe")

        ddl_label = tk.Label(master=window, text="ddl", relief="flat", width=12)
        ddl_label.grid(row=0, column=5, sticky="nswe")
        ddl = tk.Entry(window)
        ddl.grid(row=1, column=5, sticky="nswe")

        link_label = tk.Label(master=window, text="link", relief="flat", width=12)
        link_label.grid(row=2, column=1, sticky="nswe", columnspan=2)
        link = tk.Entry(window)
        link.grid(row=3, column=1, sticky="nswe", columnspan=2)

        start_label = tk.Label(master=window, text="start (hh:mm:ss)", relief="flat", width=12)
        start_label.grid(row=2, column=3, sticky="nswe")
        start = tk.Entry(window)
        start.grid(row=3, column=3, sticky="nswe")

        end_label = tk.Label(master=window, text="end (hh:mm:ss)", relief="flat")
        end_label.grid(row=2, column=4, sticky="nswe")
        end = tk.Entry(window)
        end.grid(row=3, column=4, sticky="nswe")

        codec_label = tk.Label(master=window, text="codec", relief="flat")
        codec_label.grid(row=2, column=5, sticky="nswe")
        codec = tk.Entry(window)
        codec.grid(row=3, column=5, sticky="nswe")

        button_create = tk.Button(window, text="Create",
                                  command=lambda: self.create_entry(name.get(), type_id.get(), set_id.get(),
                                                                    entry.get(), [t_init.get(), rul.get(), (rdl.get()),
                                                                                  dul.get(), ddl.get(), link.get(),
                                                                                  start.get(), end.get(), codec.get()]))
        button_create.grid(row=5, column=5, sticky="nswe")

        name_label = tk.Label(master=window, text="File Name", relief="flat")
        name_label.grid(row=4, column=1, sticky="nswe")
        name = tk.Entry(window)
        name.grid(row=5, column=1, sticky="nswe")

        dropdown_label = tk.Label(master=window, text="Type ID", relief="flat")
        dropdown_label.grid(row=4, column=2, sticky="nswe")
        dropdown = tk.OptionMenu(window, type_id, "VS", "WB")
        dropdown.grid(row=5, column=2, sticky="nswe")

        set_label = tk.Label(master=window, text="Set ID", relief="flat")
        set_label.grid(row=4, column=3, sticky="nswe")
        set_id = tk.Entry(window)
        set_id.grid(row=5, column=3, sticky="nswe")

        entry_label = tk.Label(master=window, text="Entry ID", relief="flat")
        entry_label.grid(row=4, column=4, sticky="nswe")
        entry = tk.Entry(window)
        entry.grid(row=5, column=4, sticky="nswe")

        # sets the title of the
        # Toplevel widget
        window.title("Create Custom Entry")

        # sets the geometry of toplevel
        window.geometry("1000x150")

        # A Label widget to show in toplevel


class FasterScrollCheckboxTreeview(CheckboxTreeview):
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
