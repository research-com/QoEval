import tkinter as tk
import psutil
from config import *
from tkinter import filedialog
from qoemu_pkg.configuration import *
import logging as log


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
        self.select_device_frame = SelectMobiledeviceTypeFrame(self)
        self.select_device_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # AdbDeviceSerial
        self.adb_device_serial_frame = AdbDeviceSerialFrame(self)
        self.adb_device_serial_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # SetDeviceFrameFrame
        self.device_frame_select_frame = SetDeviceFrameFrame(self)
        self.device_frame_select_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Resolution
        # self.resolution_frame = ResolutionFrame(self)
        # self.resolution_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Exempt Ports
        self.expemt_ports_frame = ExemptPortsFrame(self)
        self.expemt_ports_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Output Folder
        self.output_folder_frame = SelectOutputFolderFrame(self)
        self.output_folder_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)

        # Upload Destiation
        # self.upload_destination_frame = SelectUploadFrame(self)
        # self.upload_destination_frame.pack(fill=tk.BOTH, expand=False, side="top", padx=5, pady=2)


class SelectMobiledeviceTypeFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.device = tk.StringVar(self)
        self.device.set("Not Selected")

        self.label = tk.Label(master=self, text="Device:    ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.dropdown = tk.OptionMenu(self, self.device, *[e.value for e in MobileDeviceType])
        self.dropdown.pack(fill=tk.BOTH, expand=1, side="right")

        self.device.trace_add("write", self._update_config)

    def _update_config(self, *args):
        config.emulator_type.set(MobileDeviceType(self.device.get()))
        log.debug(f"Config: Emulator type set to: {config.emulator_type.get()}")


class AdbDeviceSerialFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.serial = tk.StringVar(self)
        self.serial.set(config.adb_device_serial.get())

        self.label = tk.Label(master=self, text="ADB Device Serial:    ")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")

        self.label_serial = tk.Label(master=self, textvariable=self.serial, width=20)
        self.label_serial.pack(fill=tk.BOTH, expand=0, side="left")

        self.button = tk.Button(self, text="Set", command=self._update_config)
        self.button.pack(side="left", expand=0, padx=40, pady=1)

        self.input = tk.Entry(self)
        self.input.insert(0, self.serial.get())
        self.input.pack(fill=tk.BOTH, expand=1, side="right")

    def _update_config(self, *args):
        self.serial.set(self.input.get())
        config.adb_device_serial.set(self.serial.get())
        log.debug(f"Config: ADB Device Serial  set to: {config.adb_device_serial.get()}")


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

        self.interface.trace_add("write", self._update_config)

    def _update_config(self, *args):
        config.net_device_name.set(self.interface.get())
        log.debug(f"Config: Net device name set to: {config.net_device_name.get()}")


class SelectOutputFolderFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        self.path = tk.StringVar(self)
        self.path.set(os.path.expanduser(config.video_capture_path.get()))

        self.button = tk.Button(self, text="Select Output Folder", command=self.open_folder)
        self.button.pack(fill=tk.BOTH, side="top", expand=1)

        self.entry = tk.Entry(self, textvariable=self.path)
        self.entry.pack(fill=tk.BOTH, side="top", expand=1)

    def open_folder(self):
        self.path.set(filedialog.askdirectory())
        config.video_capture_path.set(self.path.get().replace(os.path.expanduser('~'), '~', 1))
        log.debug(f"Config: Video capture path set to: {config.video_capture_path.get()}")



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
        self.set_off = tk.Radiobutton(self, text="False", variable=self.is_device_frame_on,
                                      value=False)
        self.set_off.pack(fill=tk.BOTH, expand=1, side="right")
        self.set_on = tk.Radiobutton(self, text="True", variable=self.is_device_frame_on,
                                     value=True)
        self.set_on.pack(fill=tk.BOTH, expand=1, side="right")

        self.is_device_frame_on.trace_add("write", self._update_config)

    def _update_config(self, *args):
        config.show_device_frame.set(self.is_device_frame_on.get())
        log.debug(f"Config: Show device frame set to: {config.show_device_frame.get()}")



class ResolutionFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master
        self.resolution = tk.IntVar(self)

        self.label = tk.Label(master=self, text="Resolution:")
        self.label.pack(fill=tk.BOTH, expand=0, side="left")
        self.set_file = tk.Radiobutton(self, text="File", variable=self.resolution,
                                       value=-1)
        self.set_file.pack(fill=tk.BOTH, expand=1, side="left")
        self.set_auto = tk.Radiobutton(self, text="Auto", variable=self.resolution,
                                       value=0)
        self.set_auto.pack(fill=tk.BOTH, expand=1, side="left")
        self.set_360 = tk.Radiobutton(self, text="360p", variable=self.resolution,
                                      value=360)
        self.set_360.pack(fill=tk.BOTH, expand=1, side="left")
        self.set_480 = tk.Radiobutton(self, text="480p", variable=self.resolution,
                                      value=480)
        self.set_480.pack(fill=tk.BOTH, expand=1, side="left")
        self.set_720 = tk.Radiobutton(self, text="720p", variable=self.resolution,
                                      value=720)
        self.set_720.pack(fill=tk.BOTH, expand=1, side="left")
        self.set_1080 = tk.Radiobutton(self, text="1080p", variable=self.resolution,
                                       value=1080)
        self.set_1080.pack(fill=tk.BOTH, expand=1, side="left")


class ExemptPortsFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, background="#DCDCDC", bd=2, relief=RELIEF)
        self.master = master

        scrollbar = tk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")



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
        self.button_add_port.pack(fill=tk.BOTH, side="top", expand=0)

        self.button_delete_port = tk.Button(self.button_frame, text="Delete Port",
                                            command=self.delete_port)
        self.button_delete_port.pack(fill=tk.BOTH, side="top", expand=0)

        self.initial_ports = tk.StringVar()
        self.initial_ports.set(config.excluded_ports.get())

        self.listbox = tk.Listbox(self, listvariable=self.initial_ports, height=1)
        self.listbox.pack(fill=tk.BOTH, expand=1, side="top")

        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)

    def delete_port(self):
        try:
            self.listbox.delete(self.listbox.curselection())
        except tk.TclError:
            pass

        self._update_config()

    def add_port(self):
        try:
            port = int(self.input.get())
            if port in range(1, 65535) and port not in self.listbox.get(0, "end"):
                self.listbox.insert('end', port)
        except ValueError:
            pass

        self._update_config()
        self.input.delete(0, "end")

    def _update_config(self):
        config.excluded_ports.set([int(element) for element in self.listbox.get(0, tk.END)])
        log.debug(f"Config: Excluded ports set to: {config.excluded_ports.get()}")
