#!/usr/bin/env python3
"""
    Screen capturing
"""

import logging as log
import os
import subprocess
import time
import shlex
import Xlib
import Xlib.display
from collections import namedtuple
from qoemu_pkg.configuration import config

# Define constants
FFMPEG = "ffmpeg"
FFMPEG_FORMAT = "x11grab"
CAPTURE_FPS = "30"  # rate in FPS
CAPTURE_DEFAULT_REC_TIME = "00:00:30"
DISPLAY = "1"

SDK_EMULATOR_WINDOW_TITLE = "Android Emulator"
GENYMOTION_EMULATOR_WINDOW_TITLE = "- Genymotion"

# Define data structures and tuples
WinGeo = namedtuple('WinGeo', 'x y height width')


def check_env():
    log.info("checking availability of ffpeg...")
    check_ext(FFMPEG)
    check_ffmpeg_features()

    if not os.path.exists(config.video_capture_path.get()):
        log.debug(f"output directory \"{config.video_capture_path.get()}\" does not exist - trying to create it")
        os.makedirs(config.video_capture_path.get())

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

    def start_recording(self, output_filename: str, duration: str=CAPTURE_DEFAULT_REC_TIME, audio: bool=True):
        raise RuntimeError(f"Method not implemented.");

SCREENCOPY_NAME = "scrcpy"
SCREENCOPY_OPTIONS ="--stay-awake -N --record"  # note: must end with option for file recording

class CaptureRealDevice(Capture):
    def __init__(self):
        super().__init__()
        check_ext(SCREENCOPY_NAME)

    def start_recording(self, output_filename: str, duration: str=CAPTURE_DEFAULT_REC_TIME, audio: bool=True):
        # start video recording from real device
        ts = time.strptime(duration, "%H:%M:%S")
        duration_in_secs = ts.tm_hour * 3600 + ts.tm_min * 60 + ts.tm_sec

        dest_tmp = os.path.join(config.video_capture_path.get(), 'captured_realdev')
        dest = os.path.join(config.video_capture_path.get(), output_filename)
        scrcpy_output = subprocess.Popen(shlex.split(f"{SCREENCOPY_NAME} {SCREENCOPY_OPTIONS} {dest_tmp}.mp4"), stdout=subprocess.PIPE,
                       universal_newlines=True)

        if audio and config.audio_device_real.get() == '':
            log.error("Cannot capture audio - audio device not specified - check AudioDeviceReal parameter in config")
            audio = False

        if audio:
            # start audio recording - will use ffmpeg for timing the recording
            command = f"{FFMPEG} -f alsa -i {config.audio_device_real.get()} -t {duration} -y {dest_tmp}.wav"
            log.debug(f"start audio recording cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()
        else:
            # poll regularly if the process has terminated - until we have reached desired duration
            runtime_capture = 0.0
            while scrcpy_output.poll()==None and runtime_capture < duration_in_secs:
                time.sleep(1)
                runtime_capture+=1

        scrcpy_output.terminate()

        # re-encoding to compressed format (we do not delete the raw dest_tmp on purpose, so it can be compared later)
        command = f"{FFMPEG} -i {dest_tmp}.mp4 -i {dest_tmp}.wav -filter:v fps=60 -map 0:v -map 1:a " \
                  f"-c:v mpeg4 -vtag xvid -qscale:v 1 -c:a libmp3lame -qscale:a 1 -shortest -y {dest}.avi"
        log.debug(f"re-encoding cmd: {command}")
        subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                universal_newlines=True).check_returncode()

class CaptureEmulator(Capture):
    def __init__(self):
        super().__init__()
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
            # log.debug(f"Window ID: {pid} Title: {name}")
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

    def start_recording(self, output_filename: str, duration: str=CAPTURE_DEFAULT_REC_TIME, audio: bool=True):
        if audio and config.audio_device_emu.get() == '':
            log.error("Cannot capture audio - audio device not specified - check AudioDeviceEmu parameter in config")
            audio = False

        if audio:
            # pulse:
            audio_param = f"-f pulse -thread_queue_size 4096 -i {config.audio_device_emu.get()} -ac 2"
            # alsa
            # audio_param = f"-f alsa -i hw:0 -ac 2"
        else:
            audio_param = ""
        window = self.get_window(SDK_EMULATOR_WINDOW_TITLE)
        if window:
            # standard emulator has no UI elements within the window
            right_border = 0
        else:
            window = self.get_window(GENYMOTION_EMULATOR_WINDOW_TITLE)
            # define border in order not to capture Genymotion UI
            right_border = 50
        if not window:
            log.error(f"Emulator window not found - cannot start recording")
            return
        self.bring_window_to_foreground(window)
        window_pos = self.get_window_position(window)
        log.info(f'Found emulator window at {window_pos.x},{window_pos.y} dim {window_pos.width},{window_pos.height}')
        dest = os.path.join(config.video_capture_path.get(), output_filename)
        dest_tmp = os.path.join(config.video_capture_path.get(), 'captured_raw')
        # command = f"{FFMPEG} {audio_param} -f {FFMPEG_FORMAT} -draw_mouse 0 -r {FFMPEG_RATE} -s {window_pos.width}x{window_pos.height} " + \
        #           f"-i :{DISPLAY}+{window_pos.x},{window_pos.y} -t {FFMPEG_REC_TIME} -c:v libxvid " \
        #           f"-preset ultrafast -y {dest}.avi"
        # lossless 1: -c:v libx264 -qp 0 -pix_fmt yuv444p -preset ultrafast
        # command = f"{FFMPEG} {audio_param} -f {FFMPEG_FORMAT} -draw_mouse 0 -r {FFMPEG_RATE} -s {window_pos.width}x{window_pos.height} " + \
        #           f"-i :{DISPLAY}+{window_pos.x},{window_pos.y} -t {FFMPEG_REC_TIME} "+ \
        #           f"-c:v libx264 -qp 0 -pix_fmt yuv444p -preset ultrafast -y {dest}.avi"

        # lossless 2: -qscale 0 -vcodec huffyuv
        command = f"{FFMPEG} -thread_queue_size 1024 {audio_param} -thread_queue_size 1024 " + \
                  f"-f {FFMPEG_FORMAT} -draw_mouse 0 -r {CAPTURE_FPS} -s {window_pos.width - right_border}x{window_pos.height} " + \
                  f"-i :{DISPLAY}+{window_pos.x},{window_pos.y} -t {duration} " + \
                  f"-acodec pcm_s16le -ar 44100 " + \
                  f"-qscale 0 -vcodec huffyuv -y {dest_tmp}.avi"

        log.debug(f"cmd: {command}")
        subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                universal_newlines=True).check_returncode()

        # re-encoding to compressed format (we do not delete the raw dest_tmp on purpose, so it can be compared later)
        command = f"{FFMPEG} -i {dest_tmp}.avi -c:v mpeg4 -vtag xvid -filter:v fps=60 -qscale:v 1 " \
                  f"-c:a libmp3lame -qscale:a 1 -y {dest}.avi"
        log.debug(f"re-encoding cmd: {command}")
        subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                universal_newlines=True).check_returncode()


if __name__ == '__main__':
    # executed directly as a script
    print("QoE screen capturing")
    # cap = CaptureEmulator()
    cap = CaptureRealDevice()
    cap.start_recording("output")
