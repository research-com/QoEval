#!/usr/bin/env python3
"""
    Screen capturing
"""

import logging as log
import subprocess
import shlex
import Xlib
import Xlib.display
from collections import namedtuple

# Define constants
FFMPEG = "ffmpeg"
FFMPEG_FORMAT = "x11grab"
FFMPEG_RATE = "30"  # rate in FPS
FFMPEG_REC_TIME = "00:00:30"
DISPLAY = "1"

# Define data structures and tuples
WinGeo = namedtuple('WinGeo', 'x y height width')


def check_env():
    log.info("checking availability of ffpeg...")
    check_ext(FFMPEG)
    check_ffmpeg_features()


def check_ext(name):
    log.debug(f"locating {name}")
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - did you run install.sh?")
        raise RuntimeError('External component not found.')
    else:
        log.debug(f"using {output.stdout}")


def check_ffmpeg_features():
    log.debug(f"checking if all required ffmpeg features are available")
    output = subprocess.run([FFMPEG, "-formats"], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if output.stdout.find(FFMPEG_FORMAT) == -1:
        log.error(f"ffmpeg does not support format {FFMPEG_FORMAT}")
        raise RuntimeError('Installed ffmpeg does not support a required format.')


class Capture:
    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        check_env()
        self._display = Xlib.display.Display()
        self._root = self._display.screen().root

    def get_absolute_geometry(self, win):
        """
        Returns the (x, y, height, width) of a window relative to the top-left
        of the screen.

        see https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib
        """
        geom = win.get_geometry()
        (x, y) = (geom.x, geom.y)
        while True:
            parent = win.query_tree().parent
            pgeom = parent.get_geometry()
            x += pgeom.x
            y += pgeom.y
            if parent.id == self._root.id:
                break
            win = parent
        return WinGeo(x, y, geom.height, geom.width)

    def get_window(self, title):
        """
        Get resource object of window which has the specified title (fragment)

        :param title: title of window to search
        :return: resource object of window if found, None otherwise
        """

        log.debug(f"getting window information for window with title \"{title}\"")
        window_ids = self._root.get_full_property(self._display.intern_atom('_NET_CLIENT_LIST'),
                                                  Xlib.X.AnyPropertyType).value
        for window_id in window_ids:
            window = self._display.create_resource_object('window', window_id)
            name = window.get_wm_name()  # Title
            prop = window.get_full_property(self._display.intern_atom('_NET_WM_PID'), Xlib.X.AnyPropertyType)
            pid = prop.value[0]  # PID
            log.debug(f"Window ID: {pid} Title: {name}")
            if name and not name.isspace() and name.find(title) != -1:
                # found the window
                return window
        log.error(f"Window with title \"{title}\" not found")
        return None

    def get_window_position(self, window):
        """
        Returns the (x, y, height, width) of a window with the specified title relative to the top-left
        of the screen.

        :param window: window object
        :return: WinGeo object with window coordinates
        """

        if window:
            return self.get_absolute_geometry(window)
        else:
            return None

    def bring_window_to_foreground(self, window):
        """
        Bring a window to the foreground of the current display
        :param window: Resource object of the window
        :return: True if successful, False otherwise
        """
        # window.raise_window()
        window.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
        window.configure(stack_mode=Xlib.X.Above)
        self._display.sync()

    def start_recording(self, output_filename):
        window = self.get_window("Android Emulator")
        if not window:
            log.error(f"Emulator window not found - cannot start recording")
            return
        self.bring_window_to_foreground(window)
        window_pos = self.get_window_position(window)
        log.info(f'Found emulator window at {window_pos.x},{window_pos.y} dim {window_pos.width},{window_pos.height}')
        command = f"{FFMPEG} -f {FFMPEG_FORMAT} -draw_mouse 0 -r {FFMPEG_RATE} -s {window_pos.width}x{window_pos.height} " + \
                  f"-i :{DISPLAY}+{window_pos.x},{window_pos.y} -t {FFMPEG_REC_TIME} -y {output_filename}.mp4"
        log.debug(f"cmd: {command}")
        output = subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                universal_newlines=True)


if __name__ == '__main__':
    # executed directly as a script
    print("QoE screen capturing")
    cap = Capture()
    cap.start_recording("output")
