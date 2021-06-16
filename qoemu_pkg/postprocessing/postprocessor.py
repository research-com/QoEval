import logging as log
import os
import tempfile
import subprocess
import shlex
import importlib_resources
from qoemu_pkg.configuration import video_capture_path, audio_device_emu, audio_device_real
from qoemu_pkg.videos import t_init

FFMPEG = "ffmpeg"
PRESERVE_TEMP_FILES = False   # True: preserve temporary processing files (e.g. for debugging), False: delete them

class PostProcessor:
    def __init__(self):
        self._prefix_video = importlib_resources.files(t_init) / "youtube_tinit.avi"
        log.debug(f"Using prefix video {self._prefix_video} for post-processing.")

    def process(self,  input_filename: str,  output_filename: str, initbuf_len: str, main_video_start_time: str, main_video_duration: str = None):
        tmp_dir = tempfile.mkdtemp()

        with importlib_resources.as_file(self._prefix_video) as prefix_video_path:
            # Note: We do a 3-step procedure here while a single split and combine ffmpeg command could also be used.
            #       However, it seems that splitting and combining leads to recoding which we would like to avoid.
            #
            # Step 1: Create prefix-video with desired length
            video_step1 = f"{os.path.join(tmp_dir, 'step_1')}.avi"
            command = f"{FFMPEG} -i {prefix_video_path} -vcodec copy -acodec copy -t {initbuf_len} " \
                      f"{video_step1} "
            log.debug(f"postproc initbuf cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                    universal_newlines=True).check_returncode()
            # Step 2: Cut main stimuli video
            video_step2 = f"{os.path.join(tmp_dir, 'step_2')}.avi"
            if main_video_duration:
                param_duration = f"-t {main_video_duration}"
            else:
                param_duration = ""

            command = f"{FFMPEG} -i {os.path.join(video_capture_path, input_filename)}.avi -vcodec copy -acodec copy " \
                      f"-ss {main_video_start_time}" \
                      f" {param_duration} {video_step2} "
            log.debug(f"postproc main cut cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                    universal_newlines=True).check_returncode()
            # Step 3: Create list of files to be concatenated
            input_list = f"{os.path.join(tmp_dir, 'input_list')}.txt"
            with open(input_list, 'w') as file:
                file.write(f"file \'{video_step1}\'\n")
                file.write(f"file \'{video_step2}\'\n")
            # Step 4: Concatenate prefix and shortened main stimuli video to create post-processed video
            command = f"{FFMPEG} -f concat -safe 0 -i \"{input_list}\" -vcodec copy -acodec copy " \
                      f"-y {os.path.join(video_capture_path, output_filename)}.avi "
            log.debug(f"postproc concat cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                                    universal_newlines=True).check_returncode()
        # clean up temporary directory
        if not PRESERVE_TEMP_FILES:
            os.remove(video_step1)
            os.remove(video_step2)
            os.remove(input_list)
            os.removedirs(tmp_dir)