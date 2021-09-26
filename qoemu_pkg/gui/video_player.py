from __future__ import annotations

import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from typing import TYPE_CHECKING
import vlc
from PIL import ImageTk, Image
import sys

if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui


class VideoPlayer(tk.Tk):

    def __init__(self, args):
        tk.Tk.__init__(self)
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (w, h))

        self.trigger_path = os.path.expanduser(args[0])
        if not os.path.exists(self.trigger_path):
            os.makedirs(self.trigger_path)

        self.video_paths = args[1:]
        self.is_dual_play = True if len(self.video_paths) > 1 else False

        if self.is_dual_play:
            self.title("LEFT: " + os.path.split(self.video_paths[0])[1] + " / "
                                                                          "RIGHT: " +
                       os.path.split(self.video_paths[1])[1])
        else:
            self.title(os.path.split(self.video_paths[0])[1])

        self.video_frames = []

        for video_path in self.video_paths:
            video_player_frame = VideoPlayerFrame(self, video_path)
            video_player_frame.pack(fill=tk.BOTH, expand=1, side=tk.LEFT)
            self.video_frames.append(video_player_frame)

    def go_to_all(self):
        for frame in self.video_frames:
            frame.go_to()

    def second_forward_all(self):
        for frame in self.video_frames:
            frame.second_forward(force=True)

    def frame_forward_all(self):
        for frame in self.video_frames:
            frame.frame_forward(force=True)

    def frames_forward_all(self):
        for frame in self.video_frames:
            frame.frames_forward(force=True)

    def frame_backward_all(self):
        for frame in self.video_frames:
            frame.frame_backward(force=True)

    def frames_backward_all(self):
        for frame in self.video_frames:
            frame.frames_backward(force=True)

    def second_backward_all(self):
        for frame in self.video_frames:
            frame.second_backward(force=True)

    def update_sync_buttons(self):
        if any([frame.player.is_playing() for frame in self.video_frames]):
            for frame in self.video_frames:
                frame.button_play_sync.configure(text="Pause all")
        else:
            for frame in self.video_frames:
                frame.button_play_sync.configure(text="Play all")

    def play_sync(self):
        if any([frame.player.is_playing() for frame in self.video_frames]):
            for frame in self.video_frames:
                frame.play_pause(force_pause=True)
        else:
            for frame in self.video_frames:
                frame.play_pause()


class VideoPlayerFrame(tk.Frame):

    def __init__(self, master: VideoPlayer, file_path):
        # A Label widget to show in toplevel
        tk.Frame.__init__(self)

        self.master = master
        self.file_path = file_path
        self.vlc_instance = _get_vlc_instance()
        self.stimulus_type_and_table_id = _get_stimulus_type_and_table_id(self.file_path)
        self.media = _get_media(self.vlc_instance, self.file_path)
        self.player = _get_player(self.vlc_instance)
        self.player.set_media(self.media)
        self.loaded_media_mrl = self.player.get_media().get_mrl()

        # base level
        self.buttons_panel = tk.Frame(self)
        self.video_panel = ttk.Frame(self)
        self.frame_slider = ttk.Frame(self)

        # video panel
        self.canvas = tk.Canvas(self.video_panel)

        # buttons panel
        self.button_pause = tk.Button(self.buttons_panel, text="playpause", command=self.play_pause, width=3)
        self.button_play_sync = tk.Button(self.buttons_panel, text="Play all", command=self.master.play_sync,
                                          width=5)
        self.button_bookmark_go_to = tk.Button(self.buttons_panel, text="Go to", width=5, command=self.go_to)
        self.button_bookmark_go_to_all = tk.Button(self.buttons_panel, text="Go to all", width=8,
                                                   command=self.go_to_all)
        self.bookmark_time = tk.IntVar()
        self.button_bookmark_set = tk.Button(self.buttons_panel, text="Bookmark", width=8, command=self.set_bookmark)
        self.button_trigger_start = tk.Button(self.buttons_panel, text="Trigger Start", command=self.trigger_start,
                                              width=8)
        self.button_trigger_end = tk.Button(self.buttons_panel, text="Trigger End", command=self.trigger_end, width=8)
        self.is_controll_all_var = tk.BooleanVar()
        self.checkbutton_control_all = tk.Checkbutton(self.buttons_panel, text="Control all:", width=8,
                                                      variable=self.is_controll_all_var)
        self.button_second_backward = tk.Button(self.buttons_panel, text="<<<", command=self.second_backward, width=1)
        self.button_frames_backward = tk.Button(self.buttons_panel, text="<<", command=self.frames_backward, width=1)
        self.button_frame_backward = tk.Button(self.buttons_panel, text="<", command=self.frame_backward, width=1)
        self.button_frame_forward = tk.Button(self.buttons_panel, text=">", command=self.frame_forward, width=1)
        self.button_frames_forward = tk.Button(self.buttons_panel, text=">>", command=self.frames_forward, width=1)
        self.button_second_forward = tk.Button(self.buttons_panel, text=">>>", command=self.second_forward, width=1)
        self.button_mute = tk.Button(self.buttons_panel, text="Mute", command=self.mute, width=4)

        # slider frame
        self.timeVar = tk.DoubleVar()
        self.timeSliderLast = 0
        self.timeSlider = tk.Scale(self.frame_slider, variable=self.timeVar, command=self.on_time,
                                   from_=0, to=0, orient=tk.HORIZONTAL, length=500,
                                   showvalue=0)  # label='Time',
        self.timeSliderUpdate = time.time()

        # pack
        self._pack_base_level()
        self._pack_video_panel()
        self._pack_buttons_panel()
        self._pack_frame_slider()
        self._attach_player_to_canvas()

        self.on_tick()

    def go_to(self):
        self.player.set_time(self.bookmark_time.get())

    def go_to_all(self):
        self.master.go_to_all()

    def set_bookmark(self):
        self.bookmark_time.set(self.player.get_time())

    def _attach_player_to_canvas(self):
        h = self.canvas.winfo_id()
        self.player.set_xwindow(h)

    def _pack_base_level(self):
        self.video_panel.pack(fill=tk.BOTH, expand=1, side=tk.TOP)
        self.frame_slider.pack(side=tk.TOP, fill=tk.X)
        self.buttons_panel.pack(expand=0, side=tk.TOP)

    def _pack_video_panel(self):
        self.canvas.pack(fill=tk.BOTH, expand=1)

    def _pack_buttons_panel(self):
        self.button_pause.pack(side=tk.LEFT, expand=0)
        if self.master.is_dual_play:
            self.button_play_sync.pack(side=tk.LEFT, expand=0)
        self.button_bookmark_set.pack(side=tk.LEFT, expand=0)
        self.button_bookmark_go_to.pack(side=tk.LEFT, expand=0)
        if self.master.is_dual_play:
            self.button_bookmark_go_to_all.pack(side=tk.LEFT, expand=0)
        self.button_trigger_start.pack(side=tk.LEFT, expand=0)
        self.button_trigger_end.pack(side=tk.LEFT, expand=0)
        self.checkbutton_control_all.pack(side=tk.LEFT, expand=0)
        self.button_second_backward.pack(side=tk.LEFT, expand=0)
        self.button_frames_backward.pack(side=tk.LEFT, expand=0)
        self.button_frame_backward.pack(side=tk.LEFT, expand=0)
        self.button_frame_forward.pack(side=tk.LEFT, expand=0)
        self.button_frames_forward.pack(side=tk.LEFT, expand=0)
        self.button_second_forward.pack(side=tk.LEFT, expand=0)
        self.button_mute.pack(side=tk.LEFT, expand=0)

    def _pack_frame_slider(self):
        self.timeSlider.pack(side=tk.BOTTOM, fill=tk.X, expand=1)

    def mute(self):
        self.player.audio_toggle_mute()
        self.update_mute_status()

    def frame_forward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.frame_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 33)

    def frame_backward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.frame_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 33)

    def frames_forward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.frames_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 333)

    def frames_backward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.frames_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 333)

    def second_forward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.second_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 1000)

    def second_backward(self, force=False):
        if self.is_controll_all_var.get() and not force:
            self.master.second_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 1000)

    def trigger_start(self):
        self.take_screenshot(True)

    def trigger_end(self):
        self.take_screenshot(False)

    def take_screenshot(self, is_start: bool):
        suffix = "_start.png" if is_start else "_end.png"
        x, y = self.player.video_get_size()
        path = os.path.join(os.path.expanduser(self.master.trigger_path), self.stimulus_type_and_table_id + suffix)
        self.player.video_take_snapshot(0, path, x, y)

    def play_pause(self, force_pause=False):
        if self.player.is_playing():
            self.button_pause.configure(text="Play")
            self.player.pause()
        elif self.player.will_play() and not force_pause:
            self.player.play()
            self.button_pause.configure(text="Pause")
        elif not force_pause:
            self.player.set_media(self.media)
            self.player.play()
            self.player.set_time(int(self.timeVar.get() * 1e1))
            self.button_pause.configure(text="Pause")

    def update_mute_status(self):
        if self.player.is_playing():
            if self.player.audio_get_mute():
                self.button_mute.configure(text="Unmute")
            else:
                self.button_mute.configure(text="Mute")

    def stop(self):
        self.player.stop()

    def on_time(self, *unused):
        if self.player:
            t = self.timeVar.get()
            if self.timeSliderLast != int(t):
                # this is a hack. The timer updates the time slider.
                # This change causes this rtn (the 'slider has changed' rtn)
                # to be invoked.  I can't tell the difference between when
                # the user has manually moved the slider and when the timer
                # changed the slider.  But when the user moves the slider
                # tkinter only notifies this rtn about once per second and
                # when the slider has quit moving.
                # Also, the tkinter notification value has no fractional
                # seconds.  The timer update rtn saves off the last update
                # value (rounded to integer seconds) in timeSliderLast if
                # the notification time (sval) is the same as the last saved
                # time timeSliderLast then we know that this notification is
                # due to the timer changing the slider.  Otherwise the
                # notification is due to the user changing the slider.  If
                # the user is changing the slider then I have the timer
                # routine wait for at least 2 seconds before it starts
                # updating the slider again (so the timer doesn't start
                # fighting with the user).
                self.player.set_time(int(t * 1e1))  # milliseconds
                self.timeSliderUpdate = time.time()

                if self.player.get_media().get_mrl() != self.loaded_media_mrl:
                    self.player.set_media(self.media)

    def on_tick(self):
        """Timer tick, update the time slider to the video time.
        """
        self.update_mute_status()
        if self.player:
            if self.player.is_playing():
                self.button_pause.configure(text="Pause")
            else:
                self.button_pause.configure(text="Play")
            self.master.update_sync_buttons()
            # since the self.player.get_length may change while
            # playing, re-set the timeSlider to the correct range
            t = self.player.get_length() * 1e-1  # to seconds
            if t > 0:
                self.timeSlider.config(to=t)

                t = self.player.get_time() * 1e-1  # to seconds
                # don't change slider while user is messing with it
                if t > 0 and time.time() > (self.timeSliderUpdate + 2):
                    self.timeSlider.set(t)
                    self.timeSliderLast = int(self.timeVar.get())
        # start the 1 second timer again
        self.after(500, self.on_tick)

        # adjust window to video aspect ratio, done periodically
        # on purpose since the player.video_get_size() only
        # returns non-zero sizes after playing for a while
        # if not self._geometry:
        #     self.OnResize()


def _get_media(vlc_instance: vlc.Instance, file_path=str):
    return vlc_instance.media_new(str(file_path))


def _get_player(vlc_instance: vlc.Instance):
    return vlc_instance.media_player_new()


def _get_vlc_instance():
    return vlc.Instance(['--no-xlib'])


def _get_stimulus_type_and_table_id(file_path):
    result = os.path.split(file_path)[1]
    result = "-".join(result.split("-")[0:2])
    return result


def main(*args):
    gui = VideoPlayer(*args)
    gui.mainloop()


if __name__ == '__main__':
    main(sys.argv[1:])
