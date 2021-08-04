import logging as log
import os
import tempfile
import subprocess
import shlex
import importlib_resources
from qoemu_pkg.configuration import config
from qoemu_pkg.videos import t_init

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
MP4BOX = "MP4Box"
PRESERVE_TEMP_FILES = False  # True: preserve temporary processing files (e.g. for debugging), False: delete them
TINIT_VIDEO_LS_FILENAME = "youtube_tinit_ls_v1.mp4"  # buffering animation shown in t-init phase (landscape)
TINIT_VIDEO_PT_FILENAME = "youtube_tinit_pt_v1.mp4"  # buffering animation shown in t-init phase (portrait)
DELTA_INITBUF_VIDEO_START_MAX = 5  # maximum time difference of end of buffer initialization and video start


def _get_video_dimensions(input_filename: str):
    command = f"{FFPROBE} -v error -select_streams v:0 -show_entries stream=width,height " \
              f"-of default=nw=1:nk=1 {input_filename}"
    output = subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                            universal_newlines=True)
    output.check_returncode()
    video_width = int(output.stdout.partition('\n')[0])
    video_height = int(output.stdout.partition('\n')[2])
    return video_width, video_height


def _is_video_landscape(input_filename: str):
    (w, h) = _get_video_dimensions(input_filename)
    return w > h


def _is_video_portrait(input_filename: str):
    return not _is_video_landscape(input_filename)


def check_env(name: str):
    output = subprocess.run(['which', name], stdout=subprocess.PIPE,
                            universal_newlines=True)
    if len(output.stdout) == 0:
        log.error(f"External component {name} not found. Must be in path - please install ffmpeg and gpac.")
        raise RuntimeError('External component not found.')


class PostProcessor:
    def __init__(self):
        self._prefix_video = None
        log.debug(f"Using prefix video {self._prefix_video} for post-processing.")
        check_env(FFMPEG)
        check_env(FFPROBE)
        check_env(MP4BOX)

    def process(self, input_filename: str, output_filename: str, initbuf_len: float, main_video_start_time: float,
                main_video_duration: float):

        main_video_end_time = main_video_start_time + main_video_duration

        if _is_video_landscape(f"{os.path.join(config.video_capture_path.get(), input_filename)}.avi"):
            self._prefix_video = importlib_resources.files(t_init) / TINIT_VIDEO_LS_FILENAME
        else:
            self._prefix_video = importlib_resources.files(t_init) / TINIT_VIDEO_PT_FILENAME

        # plausibility check of time differences
        if main_video_start_time < initbuf_len:
            raise RuntimeError(
                f"Postprocessing error: Start time of main video ({main_video_start_time}s) is less than "
                f"end of buffer initialization ({initbuf_len}s).")

        if main_video_start_time - initbuf_len > DELTA_INITBUF_VIDEO_START_MAX:
            raise RuntimeError(
                f"Postprocessing plausibility check failed: "
                f"Start time of main video ({main_video_start_time}s) is more than "
                f"{DELTA_INITBUF_VIDEO_START_MAX}s later than end of buffer initialization ({initbuf_len}s).")

        # perform postprocessing
        tmp_dir = tempfile.mkdtemp()
        with importlib_resources.as_file(self._prefix_video) as prefix_video_path:
            # Note: We do a 3-step procedure here since MP4Box cannot import only a fragment.
            #       Therefore, we first import the unprocessed video. Then we cut out
            #       the relevant stimuli, and lastly we concatenate t_init waiting animation and the stimuli.
            #
            video_step1 = f"{os.path.join(tmp_dir, 'step_1')}.mp4"
            step1_audio = f"{os.path.join(tmp_dir, 'step_1_audio')}.mp3"  # audio part only
            step1_video = f"{os.path.join(tmp_dir, 'step_1_video')}.mp4"  # video part only
            command = f"{FFMPEG} -i {os.path.join(config.video_capture_path.get(), input_filename)}.avi -vn " \
                      f"-acodec copy {step1_audio}"
            log.debug(f"postproc audio extract cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            command = f"{FFMPEG} -i {os.path.join(config.video_capture_path.get(), input_filename)}.avi -an " \
                      f"-vcodec copy {step1_video}"
            log.debug(f"postproc video extract cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            command = f"{MP4BOX} -add {step1_audio} -add {step1_video}" \
                      f" -new {video_step1} "
            log.debug(f"postproc main import cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            # Step 2: Cut imported video
            video_step2 = f"{os.path.join(tmp_dir, 'step_2')}.mp4"
            command = f"{MP4BOX} -split-chunk {main_video_start_time}:{main_video_end_time} " \
                      f"{video_step1} -out {video_step2}"
            log.debug(f"postproc main cut cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            # Step 3: Concatenate prefix and shortened main stimuli video to create post-processed video
            command = f"{MP4BOX} -add  {prefix_video_path}#video:dur={initbuf_len} -cat {video_step2} " \
                      f"-new {os.path.join(config.video_capture_path.get(), output_filename)}.avi "
            log.debug(f"postproc concat cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            # Addtionally create a H.264 encoded output file
            command = f"{FFMPEG} -i {prefix_video_path} " \
                      f"-i {os.path.join(config.video_capture_path.get(), input_filename)}.avi  -crf 4 -filter_complex \"" \
                      f"[0:v]trim=0:{initbuf_len},setpts=PTS-STARTPTS[v0]; " \
                      f"[0:a]atrim=0:{initbuf_len},asetpts=PTS-STARTPTS[a0]; " \
                      f"[1:v]trim={main_video_start_time}:{main_video_end_time},setpts=PTS-STARTPTS[v1]; " \
                      f"[1:a]atrim={main_video_start_time}:{main_video_end_time},asetpts=PTS-STARTPTS[a1]; " \
                      f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]\" " \
                      f"-map \"[outv]\" -map \"[outa]\" " \
                      f" -y {os.path.join(config.video_capture_path.get(), output_filename)}.mp4"
            log.debug(f"postproc mp4 reencoded cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

        # clean up temporary directory
        if not PRESERVE_TEMP_FILES:
            os.remove(step1_audio)
            os.remove(step1_video)
            os.remove(video_step1)
            os.remove(video_step2)
            os.removedirs(tmp_dir)


if __name__ == '__main__':
    p = PostProcessor()
    p.process("WB-A-1_E1-R-0.1_P0","test",5,5,10)

    print("Done.")
