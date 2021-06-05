import tkinter as tk
import psutil
from config import *
from tkinter import filedialog


class SettingsFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=1, relief=RELIEF)
        self.master = master

        # Label
        # self.label = tk.Label(master=self, text="Emulation Settings", font=("bold", 15), relief="flat")
        # self.label.pack(fill=tk.BOTH, expand=0, side="top")

        # SelectInterfaceFrame
        self.select_interface_frame = SelectInterfaceFrame(self)
        self.select_interface_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # SelectDeviceFrame
        self.select_device_frame = SelectDeviceFrame(self)
        self.select_device_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # SetDeviceFrameFrame
        self.device_frame_select_frame = SetDeviceFrameFrame(self)
        self.device_frame_select_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # ExemptPortsFrame
        self.device_frame_select_frame = ExemptPortsFrame(self)
        self.device_frame_select_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # OutputFolderFrane
        self.device_frame_select_frame = SelectOutputFolderFrame(self)
        self.device_frame_select_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # OutputFolderFrane
        self.device_frame_select_frame = SelectUploadFrame(self)
        self.device_frame_select_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)


class SelectDeviceFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.device = tk.StringVar(self)
        self.device.set("Not Selected")

        self.label = tk.Label(master=self, text="Device:    ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self, self.device, *DEVICES)
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="right")


class SelectInterfaceFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.interface = tk.StringVar(self)
        self.interface.set("Not Selected")

        interfaces = psutil.net_if_addrs()
        interfaces.pop("lo")

        self.label = tk.Label(master=self, text="Interface: ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self, self.interface, *interfaces)
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="right")


class SelectOutputFolderFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.output_folder = tk.StringVar(self)
        self.output_folder.set("Not Selected")

        self.button = tk.Button(self, text="Select Output Folder", command=self.open_folder)
        self.button.pack(fill=tk.BOTH, side="top", expand=1)

        self.entry = tk.Entry(self, textvariable=self.output_folder)
        self.entry.pack(fill=tk.BOTH, side="top", expand=1)

    def open_folder(self):
        self.output_folder.set(filedialog.askdirectory())


class SelectUploadFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.upload_folder = tk.StringVar(self)
        self.upload_folder.set("Not Selected")

        self.label = tk.Label(self, text="Select Upload Destination ")
        self.label.pack(fill=tk.BOTH, side="top", expand=1)

        self.entry = tk.Entry(self, textvariable=self.upload_folder)
        self.entry.pack(fill=tk.BOTH, side="top", expand=1)

    def open_folder(self):
        self.upload_folder.set(filedialog.askdirectory())


class SetDeviceFrameFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.is_device_frame_on = tk.BooleanVar(self)

        self.label = tk.Label(master=self, text="Show Device Frame:")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")
        self.set_off = tk.Radiobutton(self, text="Off", variable=self.is_device_frame_on,
                                      value=False)
        self.set_off.pack(fill=tk.BOTH, expand=1, side="right")
        self.set_on = tk.Radiobutton(self, text="On", variable=self.is_device_frame_on,
                                     value=True)
        self.set_on.pack(fill=tk.BOTH, expand=1, side="right")


class ExemptPortsFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        # Label
        self.label = tk.Label(master=self, text="Exempt ports from netem", font=("", 12))
        self.label.pack(fill=tk.BOTH, expand=0, side="top")

        # button Frame
        self.button_frame = tk.Frame(self, background="#DCDCDC", bd=1, relief="sunken")
        self.button_frame.pack(fill=tk.BOTH, expand=0, side="left")

        self.input = tk.Entry(self.button_frame)
        self.input.pack(fill=tk.BOTH, expand=0, side="top")

        self.button_add_port = tk.Button(self.button_frame, text="Add Port",
                                         command=self.add_port)
        self.button_add_port.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_delete_port = tk.Button(self.button_frame, text="Delete Port",
                                            command=self.delete_port)
        self.button_delete_port.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_load_default = tk.Button(self.button_frame, text="Load Default")
        self.button_load_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.button_set_default = tk.Button(self.button_frame, text="Set Default")
        self.button_set_default.pack(fill=tk.BOTH, side="top", expand=1)

        self.initial_ports = tk.StringVar()
        self.initial_ports.set((1, 2, 3, 4))

        self.listbox = tk.Listbox(self, listvariable=self.initial_ports)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="right")

    def delete_port(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

    def add_port(self):
        try:
            port = int(self.input.get())
            if port in range(1, 65535) and port not in self.listbox.get(0, "end"):
                self.listbox.insert('end', port)
        except ValueError:
            pass

        self.input.delete(0, "end")
