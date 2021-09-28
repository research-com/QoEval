from __future__ import annotations

import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from typing import TYPE_CHECKING
import tkinter.messagebox as messagebox
import vlc
from PIL import ImageTk, Image

if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui

OPEN_FILE_TEXT = "open file"
_VIDEO = '/home/jk/stimuli/VSB-F-1_E1-R-0.5.0_P1.avi'


class ResultsFrame(tk.Frame):

    def __init__(self, master, gui: Gui):
        super().__init__(master, background="#DCDCDC", bd=1, relief="sunken")
        self.master = master
        self.gui: Gui = gui

        self.gui.updatable_elements.append(self)

        self.selected_video_paths = []
        self.filenames =[]

        self.frame_stimuli = tk.Frame(self) # , bd=0, borderwidth=1, relief=tk.SOLID)
        self.frame_stimuli.pack(side=tk.LEFT, expand=0, fill=tk.Y)

        sep = ttk.Separator(self, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, expand=0, fill=tk.Y, padx=4)

        self.label_stimuli = tk.Label(self.frame_stimuli, text="Stimuli", font=("Arial", 15), anchor=tk.W)
        self.label_stimuli.pack(side=tk.TOP, fill=tk.X, expand=tk.NO)

        self.listbox_stimuli = tk.Listbox(self.frame_stimuli, exportselection=False)
        self.listbox_stimuli.pack(side=tk.TOP, expand=1, fill=tk.Y)

        self.frame_right = tk.Frame(self)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=tk.YES)

        self.label_graphs = tk.Label(self.frame_right, text="Graphs", font=("Arial", 15), anchor=tk.W)
        self.label_graphs.pack(side=tk.TOP, fill=tk.X, expand=tk.NO)

        self.frame_graphs = tk.Frame(self.frame_right)
        self.frame_graphs.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        self.frame_graphs_listbox = tk.Frame(self.frame_graphs)
        self.frame_graphs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.NO)

        sep = ttk.Separator(self.frame_right, orient=tk.HORIZONTAL)
        sep.pack(side=tk.TOP, expand=0, fill=tk.X, pady=2)

        self.label_videos = tk.Label(self.frame_right, text="Videos (select up to two)", font=("Arial", 15), anchor=tk.W)
        self.label_videos.pack(side=tk.TOP, fill=tk.X)

        self.frame_videos = tk.Frame(self.frame_right)
        self.frame_videos.pack(side=tk.LEFT)

        self.listbox_graphs = tk.Listbox(self.frame_graphs_listbox, exportselection=False)
        self.listbox_graphs.pack(side=tk.TOP, anchor=tk.W, fill=tk.Y, expand=tk.YES)
        self.listbox_graphs.bind('<<ListboxSelect>>', self.on_graph_select)

        self.listbox_videos = tk.Listbox(self.frame_videos, exportselection=False, selectmode="multiple")
        self.listbox_videos.pack(side=tk.TOP)
        self.listbox_videos.bind('<<ListboxSelect>>', self.on_video_select)

        self.frame_preview = tk.Frame(self.frame_graphs)
        self.frame_preview.pack(side=tk.TOP)

        self.label_preview = tk.Label(self.frame_preview)
        self.label_preview.pack(side=tk.TOP)

        self.button_open_pdf = tk.Button(self.frame_graphs_listbox, text="Open PDF", command=self.open_pdf)
        self.button_open_pdf.pack(side=tk.BOTTOM, expand=tk.NO, fill=tk.X)

        self.button_play = tk.Button(self.frame_videos, text="Play selected videos", command=self.open_video_player)
        self.button_play.pack(side=tk.BOTTOM, fill=tk.X)

        self.update()

    def update(self):
        self.filenames = os.listdir(self.gui.qoemu_config.video_capture_path.get())
        self.filenames = [filename for filename in self.filenames
                          if os.path.isfile(os.path.join(self.gui.qoemu_config.video_capture_path.get(), filename))]
        stimuli = set()
        for filename in self.filenames:
            split = filename.split("_")
            stimuli.add(split[0])

        stimuli = list(stimuli)
        stimuli.sort()

        self.listbox_stimuli.delete(0, tk.END)
        for stimulus in stimuli:
            self.listbox_stimuli.insert(tk.END, stimulus)
        self.listbox_stimuli.bind('<<ListboxSelect>>', self.on_stimulus_select)

    def on_video_select(self, *unused):
        self.selected_video_paths = []
        for filename in self.filenames:
            if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
                    and any([filename.endswith(self.listbox_videos.get(index)) for index in self.listbox_videos.curselection()]):
                video_path = os.path.join(self.gui.qoemu_config.video_capture_path.get(), filename)
                self.selected_video_paths.append(video_path)

    def open_pdf(self):
        try:
            pdf_path = None
            for filename in self.filenames:
                if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
                        and filename.endswith("_stats_" + self.listbox_graphs.get(self.listbox_graphs.curselection())):
                    pdf_path = os.path.join(self.gui.qoemu_config.video_capture_path.get(), filename)
                    pdf_path = os.path.splitext(pdf_path)[0] + ".pdf"
            if pdf_path:
                subprocess.call(('xdg-open', pdf_path))
        except tk.TclError:
            pass

    def open_video_player(self):
        if len(self.selected_video_paths) > 2 or len(self.selected_video_paths) < 1:
            messagebox.showerror("Error", "Please select between 1 and 2 Videos")
            return
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "video_player.py")
        args = "~/stimuli/trigger/ " + " ".join(self.selected_video_paths)
        subprocess.Popen(f"python3 {path} {args}".split(" "), shell=False)

    def on_stimulus_select(self, *args):
        self.listbox_graphs.delete(0, tk.END)
        for filename in self.filenames:
            if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
                    and filename.endswith(".pdf"):
                self.listbox_graphs.insert(tk.END, filename.split("_stats_")[1])

        self.listbox_videos.delete(0, tk.END)
        for filename in self.filenames:
            if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
                    and (filename.endswith(".avi") or filename.endswith(".mp4")):
                self.listbox_videos.insert(tk.END, filename.split("_")[-1])

        self.listbox_graphs.selection_clear(0, tk.END)
        self.label_preview.configure(image=None)
        self.label_preview.image = None
        self.listbox_videos.selection_clear(0, tk.END)
        self.selected_video_paths = []

    def on_graph_select(self, *args):
        try:
            for filename in self.filenames:
                if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
                        and filename.endswith("_stats_" + self.listbox_graphs.get(self.listbox_graphs.curselection())):
                    image_path = os.path.join(self.gui.qoemu_config.video_capture_path.get(), filename)
                    image_path = os.path.splitext(image_path)[0] + ".png"

                    img = Image.open(image_path)
                    img = img.resize((400, 225))
                    tkimage = ImageTk.PhotoImage(img)
                    self.label_preview.configure(image=tkimage)
                    self.label_preview.image = tkimage
        except tk.TclError:
            pass

        # for filename in self.filenames:
        #     if filename.startswith(self.listbox_stimuli.get(self.listbox_stimuli.curselection())) \
        #                 and filename.endswith("_stats_" + self.listbox_graphs.get(self.listbox_graphs.curselection())):
        #         pdf_location = os.path.join(self.gui.qoemu_config.video_capture_path.get(), filename)
        #         subprocess.call(('xdg-open', pdf_location))
