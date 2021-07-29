import logging as log
import os
import tempfile
import subprocess
import shlex
import importlib_resources
from qoemu_pkg.configuration import config
from qoemu_pkg.videos import t_init

FFMPEG = "ffmpeg"
MP4BOX = "MP4Box"
PRESERVE_TEMP_FILES = True   # True: preserve temporary processing files (e.g. for debugging), False: delete them
TINIT_VIDEO_FILENAME = "youtube_tinit.avi"


class PostProcessor:
    def __init__(self):
        self._prefix_video = importlib_resources.files(t_init) / TINIT_VIDEO_FILENAME
        log.debug(f"Using prefix video {self._prefix_video} for post-processing.")
        self.check_env(FFMPEG)
        self.check_env(MP4BOX)

    def check_env(self, name: str):
        output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                                universal_newlines=True)
        if len(output.stdout) == 0:
            log.error(f"External component {name} not found. Must be in path - please install ffmpeg and gpac.")
            raise RuntimeError('External component not found.')

    def process(self,  input_filename: str,  output_filename: str, initbuf_len: float, main_video_start_time: float, main_video_duration: float):
        tmp_dir = tempfile.mkdtemp()

        with importlib_resources.as_file(self._prefix_video) as prefix_video_path:
            # Note: We do a 3-step procedure here since MP4Box cannot import only a fragment.
            #       Therefore, we first import the unprocessed video. Then we cut out
            #       the relevant stimuli, and lastly we concatenate t_init waiting animation and the stimuli.
            #
            # Step 1: Convert/import input video
            video_step1 = f"{os.path.join(tmp_dir, 'step_1')}.avi"
            command = f"{MP4BOX} -add {os.path.join(config.video_capture_path.get(), input_filename)}.avi" \
                      f" -new {video_step1} "
            log.debug(f"postproc main import cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                    universal_newlines=True).check_returncode()

            # Step 2: Cut imported video
            video_step2 = f"{os.path.join(tmp_dir, 'step_2')}.avi"
            command = f"{MP4BOX} -v -split-chunk {main_video_start_time}:{main_video_start_time+main_video_duration} " \
                      f"{video_step1} -out {video_step2}"
            log.debug(f"postproc main cut cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            # Step 3: Concatenate prefix and shortened main stimuli video to create post-processed video
            command = f"{MP4BOX} -v -add  {prefix_video_path}:dur={initbuf_len} -cat {video_step2} "\
                      f"-new {os.path.join(config.video_capture_path.get(), output_filename)}.avi "
            log.debug(f"postproc concat cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                    universal_newlines=True).check_returncode()
        # clean up temporary directory
        if not PRESERVE_TEMP_FILES:
            os.remove(video_step1)
            os.remove(video_step2)
            os.removedirs(tmp_dir)