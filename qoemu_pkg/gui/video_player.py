from __future__ import annotations

import os
import time
import tkinter as tk
from tkinter import ttk
import vlc
import tkinter.messagebox as messagebox
import sys

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoemu_pkg.gui.gui import Gui

# Parts of this code is copied from:
# https://github.com/oaubert/python-vlc/blob/master/examples/tkvlc.py
#
# License:
#
# tkinter example for VLC Python bindings
# Copyright (C) 2015 the VideoLAN team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 021
# """A simple example for VLC python bindings using tkinter.
# Requires Python 3.4 or later.
# Author: Patrick Fay
# Date: 23-09-2015
# """

class VideoPlayer(tk.Tk):

    """Root level GUI for playing back up to two videos. Expects a "trigger image path" as first argument and up to two
    video file paths as second (and third) argument"""

    def __init__(self, args):
        tk.Tk.__init__(self)
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (w, h))

        self.trigger_path = os.path.expanduser(args[0])
        if not os.path.exists(self.trigger_path):
            os.makedirs(self.trigger_path)

        print(self.trigger_path)

        self.video_paths = args[1:3]
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
            frame.go_to(force=True)

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

    def update_play_buttons(self):
        """Update play/pause buttons for all players"""
        is_any_player_playing = any([frame.player.is_playing() for frame in self.video_frames])
        for frame in self.video_frames:
            frame.update_play_pause_button(is_any_player_playing)

    def toggle_mute_all(self):
        for frame in self.video_frames:
            frame.toggle_mute(force=True)
            frame.update_mute_status()

    def set_bookmark_all(self):
        for frame in self.video_frames:
            frame.set_bookmark(force=True)

    def play_sync(self):
        """Play/Pauses all players in sync"""
        is_any_player_playing = any([frame.player.is_playing() for frame in self.video_frames])
        if is_any_player_playing:
            for frame in self.video_frames:
                frame.play_pause(force_pause=True)
        else:
            for frame in self.video_frames:
                frame.play_pause(force_play=True)


class VideoPlayerFrame(tk.Frame):

    """A tk Frame containing a canvas and controls for video playback"""

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

        # root level
        self.buttons_panel = tk.Frame(self)
        self.video_panel = ttk.Frame(self)
        self.frame_slider = ttk.Frame(self)

        # video panel
        self.canvas = tk.Canvas(self.video_panel)

        # buttons panel
        self.button_play_pause = tk.Button(self.buttons_panel, text="playpause", command=self.play_pause, width=3)
        self.button_bookmark_go_to = tk.Button(self.buttons_panel, text="Go to", width=3, command=self.go_to)
        self.bookmark_time = tk.IntVar()
        self.bookmark_time.set(0)
        self.button_bookmark_set = tk.Button(self.buttons_panel, text="Set", width=2, command=self.set_bookmark)
        self.label_bookmark_desc = tk.Label(self.buttons_panel, text="Bookmark:", width=8)
        self.label_bookmark = tk.Label(self.buttons_panel, width=7, textvariable=self.bookmark_time)
        self.label_trigger_desc = tk.Label(self.buttons_panel, text="Trigger", width=8)
        self.button_trigger_start = tk.Button(self.buttons_panel, text="Start", command=self.trigger_start,
                                              width=3)
        self.button_trigger_end = tk.Button(self.buttons_panel, text="End", command=self.trigger_end, width=3)
        self.is_controll_all_var = tk.BooleanVar()
        self.checkbutton_control_all = tk.Checkbutton(self.buttons_panel, text="Control All   ", width=8,
                                                      variable=self.is_controll_all_var,
                                                      command=self.toggle_control_all_visual_effect)
        self.button_second_backward = tk.Button(self.buttons_panel, text="<<<", command=self.second_backward, width=1)
        self.button_frames_backward = tk.Button(self.buttons_panel, text="<<", command=self.frames_backward, width=1)
        self.button_frame_backward = tk.Button(self.buttons_panel, text="<", command=self.frame_backward, width=1)
        self.button_frame_forward = tk.Button(self.buttons_panel, text=">", command=self.frame_forward, width=1)
        self.button_frames_forward = tk.Button(self.buttons_panel, text=">>", command=self.frames_forward, width=1)
        self.button_second_forward = tk.Button(self.buttons_panel, text=">>>", command=self.second_forward, width=1)
        self.button_mute = tk.Button(self.buttons_panel, text="Mute", command=self.toggle_mute, width=4)

        # slider frame
        self.timeVar = tk.DoubleVar()
        self.timeSliderLast = 0
        self.timeSlider = tk.Scale(self.frame_slider, variable=self.timeVar, command=self.on_time,
                                   from_=0, to=0, orient=tk.HORIZONTAL, length=500,
                                   showvalue=0)  # label='Time',
        self.timeSliderUpdate = time.time()

        # pack
        self._pack_root_level()
        self._pack_video_panel()
        self._pack_buttons_panel()
        self._pack_frame_slider()
        self._attach_player_to_canvas()

        self.on_tick()

    def _attach_player_to_canvas(self):
        """ Embeds the vlc player to the frames canvas"""
        h = self.canvas.winfo_id()
        self.player.set_xwindow(h)

    def _pack_root_level(self):
        """Pack all root level widgets/frames"""
        self.video_panel.pack(fill=tk.BOTH, expand=1, side=tk.TOP)
        self.frame_slider.pack(side=tk.TOP, fill=tk.X)
        self.buttons_panel.pack(expand=0, side=tk.TOP)

    def _pack_video_panel(self):
        """Pack elements of the video panel"""
        self.canvas.pack(fill=tk.BOTH, expand=1)

    def _pack_buttons_panel(self):
        """Pack elements of the buttons panel"""
        self.checkbutton_control_all.pack(side=tk.LEFT, expand=0, fill=tk.Y)
        sep = ttk.Separator(self.buttons_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, expand=0, fill=tk.Y, padx=10)
        self.button_play_pause.pack(side=tk.LEFT, expand=0)
        self.button_second_backward.pack(side=tk.LEFT, expand=0)
        self.button_frames_backward.pack(side=tk.LEFT, expand=0)
        self.button_frame_backward.pack(side=tk.LEFT, expand=0)
        self.button_frame_forward.pack(side=tk.LEFT, expand=0)
        self.button_frames_forward.pack(side=tk.LEFT, expand=0)
        self.button_second_forward.pack(side=tk.LEFT, expand=0)
        sep = ttk.Separator(self.buttons_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, expand=0, fill=tk.Y, padx=10)
        self.label_bookmark_desc.pack(side=tk.LEFT, expand=0)
        self.label_bookmark.pack(side=tk.LEFT, expand=0)
        self.button_bookmark_set.pack(side=tk.LEFT, expand=0)
        self.button_bookmark_go_to.pack(side=tk.LEFT, expand=0)
        sep = ttk.Separator(self.buttons_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, expand=0, fill=tk.Y, padx=15)
        self.button_mute.pack(side=tk.LEFT, expand=0)
        sep = ttk.Separator(self.buttons_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, expand=0, fill=tk.Y, padx=10)
        self.label_trigger_desc.pack(side=tk.LEFT, expand=0)
        self.button_trigger_start.pack(side=tk.LEFT, expand=0)
        self.button_trigger_end.pack(side=tk.LEFT, expand=0)

    def _pack_frame_slider(self):
        """Pack elements of the slider panel"""
        self.timeSlider.pack(side=tk.BOTTOM, fill=tk.X, expand=1)

    def toggle_control_all_visual_effect(self):
        """Creates a visual feedback for the 'Control all' checkbox"""
        color = "grey" if self.is_controll_all_var.get() else "lightgrey"
        for child in self.buttons_panel.winfo_children():
            # print(child)
            if type(child) is tk.Button:
                if child != self.button_trigger_end and child != self.button_trigger_start:
                    child.configure(bg=color)

    def set_bookmark(self, force=False):
        """Bookmarks the current time of the player / all players"""
        if self.is_controll_all_var.get() and not force:
            self.master.set_bookmark_all()
        else:
            self.bookmark_time.set(self.player.get_time())

    def go_to(self, force=False):
        """Set the time of the player / all players to the saved bookmark"""
        if self.is_controll_all_var.get() and not force:
            self.master.go_to_all()
        else:
            self.player.set_time(self.bookmark_time.get())

    def toggle_mute(self, force=False):
        """Toggle the mute state of the player / all players"""
        if self.is_controll_all_var.get() and not force:
            self.master.toggle_mute_all()
        else:
            self.player.audio_toggle_mute()
            self.update_mute_status()

    def frame_forward(self, force=False):
        """Move the player / all players one frame forward"""
        if self.is_controll_all_var.get() and not force:
            self.master.frame_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 33)

    def frame_backward(self, force=False):
        """Move the player / all players one frame backward"""
        if self.is_controll_all_var.get() and not force:
            self.master.frame_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 33)

    def frames_forward(self, force=False):
        """Move the player / all players ten frames forward"""
        if self.is_controll_all_var.get() and not force:
            self.master.frames_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 333)

    def frames_backward(self, force=False):
        """Move the player / all players ten frames forward"""
        if self.is_controll_all_var.get() and not force:
            self.master.frames_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 333)

    def second_forward(self, force=False):
        """Move the player / all players one second forward"""
        if self.is_controll_all_var.get() and not force:
            self.master.second_forward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time + 1000)

    def second_backward(self, force=False):
        """Move the player / all players one second backwards"""
        if self.is_controll_all_var.get() and not force:
            self.master.second_backward_all()
        else:
            curr_time = self.player.get_time()
            self.player.set_time(curr_time - 1000)

    def trigger_start(self):
        """Save a trigger start image from the current frame"""
        self.save_snapshot(True)

    def trigger_end(self):
        """Save a trigger end image from the current frame"""
        self.save_snapshot(False)

    def trigger_get_filepath(self, is_start: bool):
        """Get the filepath to save the trigger image to"""
        suffix = "_start.png" if is_start else "_end.png"
        return os.path.join(os.path.expanduser(self.master.trigger_path), self.stimulus_type_and_table_id + suffix)

    def save_snapshot(self, is_start: bool):
        """Save a snapshot as trigger image"""
        path = self.trigger_get_filepath(is_start)
        overwrite = True
        if os.path.isfile(path):
            overwrite = messagebox.askyesno("File already exists", f"{os.path.split(path)[1]} already exists. Overwrite?")
        if overwrite:
            x, y = self.player.video_get_size()
            self.player.video_take_snapshot(0, path, x, y)

    def update_play_pause_button(self, is_any_player_playing: bool=None):
        """Updates the text of the play pause button to reflect current playback status"""
        if not self.is_controll_all_var.get():
            is_playing = self.player.is_playing()
        else:
            is_playing = is_any_player_playing
        if is_playing:
            self.button_play_pause.configure(text="Pause")
        else:
            self.button_play_pause.configure(text="Play")

    def play_pause(self, force_play=False, force_pause=False):
        """Play / pause player / all players. Reload player media if necessary"""
        if self.is_controll_all_var.get() and not force_pause and not force_play:
            self.master.play_sync()
            return
        if self.player.is_playing() and not force_play:
            self.player.pause()
            self.master.update_play_buttons()
        elif self.player.will_play() and not force_pause:
            self.player.play()
            self.master.update_play_buttons()
        elif not force_pause:
            self.player.set_media(self.media)
            self.player.play()
            self.player.set_time(int(self.timeVar.get() * 1e1))
            self.master.update_play_buttons()

    def update_mute_status(self):
        """Updates the text of the mute button to reflect current status"""
        if self.player.audio_get_mute():
            self.button_mute.configure(text="Unmute")
        else:
            self.button_mute.configure(text="Mute")

    def on_time(self, *unused):
        """Callback of the time slider. Updates the time of the player when slider was moved manually"""
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
        """Timer tick, update the time slider to the video time. Update buttons to reflect player state.
        """
        self.update_mute_status()
        if self.player:
            self.master.update_play_buttons()
            # since the self.player.get_length may change while
            # playing, re-set the timeSlider to the correct range
            t = self.player.get_length() * 1e-1  # to seconds
            if t >= 0:
                self.timeSlider.config(to=t)

                t = self.player.get_time() * 1e-1  # to seconds
                # don't change slider while user is messing with it
                if t >= 0 and time.time() > (self.timeSliderUpdate + 2):
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
    """Create a vlc media from a filepath"""
    return vlc_instance.media_new(str(file_path))


def _get_player(vlc_instance: vlc.Instance):
    """Create a vlc player"""
    return vlc_instance.media_player_new()


def _get_vlc_instance():
    """Create a vlc instance"""
    return vlc.Instance(['--no-xlib'])
    vlc_instance = vlc.Instance(['--no-xlib'])
    raise RuntimeError("Cannot get vlc instance! If you installed vlc successfully, please check "
                       "that vlc plugins are installed (on Ubuntu: \"sudo apt install vlc-plugin-base\") and"
                       "that plugins are found.")
    return vlc_instance


def _get_stimulus_type_and_table_id(file_path):
    result = os.path.split(file_path)[1]
    result = "-".join(result.split("-")[0:2])
    return result


def main(*args):
    gui = VideoPlayer(*args)
    gui.mainloop()


if __name__ == '__main__':
    main(sys.argv[1:])
