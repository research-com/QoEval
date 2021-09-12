import logging as log
import os
import re
import shlex
import subprocess

import importlib_resources

from qoemu_pkg.configuration import QoEmuConfiguration, get_default_qoemu_config
from qoemu_pkg.videos import t_init

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
MP4BOX = "MP4Box"
PRESERVE_TEMP_FILES = False  # True: preserve temporary processing files (e.g. for debugging), False: delete them
PREFIX_VIDEO_ERASE_AUDIO = True  # True: set audio volume of prefix video to 0 (no sound), False: do not modify volume
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


def _get_max_volume(input_filename: str):
    command = f"{FFMPEG} -i {input_filename} -af \"volumedetect\" -vn -sn -dn -f null /dev/null "
    output = subprocess.run(shlex.split(command), stderr=subprocess.PIPE,
                            universal_newlines=True)
    output.check_returncode()
    pattern = r"\s*max_volume:\s(-?\d*\.?\d*)\sdB*"
    matcher = re.compile(pattern)
    match = (matcher.search(output.stderr))
    if match:
        max_vol = float(match.group(1))
        log.debug(f"maximum volume in source video file: {max_vol}")
    else:
        log.error(f"Cannot determine maximum volume of video file: {input_filename}")
        raise RuntimeError('Video volume detection failed.')

    return max_vol


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
    def __init__(self, qoemu_config: QoEmuConfiguration):
        self.qoemu_config = qoemu_config
        self._prefix_video = None
        check_env(FFMPEG)
        check_env(FFPROBE)
        check_env(MP4BOX)

    def process(self, input_filename: str, output_filename: str, initbuf_len: float, main_video_start_time: float,
                main_video_duration: float, normalize_audio: bool = False, erase_audio=None, erase_box=None):

        main_video_end_time = main_video_start_time + main_video_duration

        if _is_video_landscape(f"{os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi"):
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

        # configure audio post-processing
        ffmpeg_audio_filter = ""  # default is no audio filtering
        if normalize_audio:
            target_volume = self.qoemu_config.audio_target_volume.get()
            current_volume = _get_max_volume(f"{os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi")
            if current_volume != target_volume:
                volume = target_volume - current_volume
                log.debug(f"audio normalization by {volume}dB (current volume: {current_volume}, "
                          f"target volume: {target_volume})")
                ffmpeg_audio_filter = f"volume={volume}dB,"

        # configure audio filter for prefix video
        if PREFIX_VIDEO_ERASE_AUDIO:
            prefix_video_ffmpeg_audio_filter = f"volume=enable='between(t,0,{initbuf_len})':volume=0,"
        else:
            prefix_video_ffmpeg_audio_filter = ""

        # main stimululi: configure optional muting of audio parts (e.g. to avoid static noise while rebuffering)
        if erase_audio and len(erase_audio) > 0:
            if len(erase_audio) % 2 != 0:
                raise RuntimeError(
                    f"Postprocessing error: audio erase list ({erase_audio}) must contain an even number of values.")
            for i in range(0, len(erase_audio), 2):
                t_start = erase_audio[i]
                t_end = erase_audio[i + 1]
                ffmpeg_audio_filter = f"{ffmpeg_audio_filter}volume=enable='between(t,{t_start},{t_end})':volume=0,"

        # configure optional erasing of a box (e.g. logo)
        if erase_box and len(erase_box) > 0:
            ffmpeg_video_filter = f"drawbox=x={erase_box[0]}:y={erase_box[1]}:" \
                                  f"w={erase_box[2]}:h={erase_box[3]}:color=black:t=fill,"
        else:
            ffmpeg_video_filter = ""  # default is no video filtering/erasing

        # perform postprocessing
        with importlib_resources.as_file(self._prefix_video) as prefix_video_path:
            # Create mpeg4 encoded .avi output file
            if initbuf_len > 0:
                log.debug(f"Using prefix video {self._prefix_video} for post-processing.")
                command = f"{FFMPEG} -i {prefix_video_path} " \
                          f"-i {os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi " \
                          f"-c:v mpeg4 -vtag xvid -qscale:v 1 -c:a libmp3lame -qscale:a 1 " \
                          f"-filter_complex \"" \
                          f"[0:v]trim=0:{initbuf_len},setpts=PTS-STARTPTS[v0]; " \
                          f"[0:a]atrim=0:{initbuf_len},{prefix_video_ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a0]; " \
                          f"[1:v]trim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_video_filter}setpts=PTS-STARTPTS[v1]; " \
                          f"[1:a]atrim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a1]; " \
                          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]\" " \
                          f"-map \"[outv]\" -map \"[outa]\" " \
                          f" -y {os.path.join(self.qoemu_config.video_capture_path.get(), output_filename)}.avi"
            else:
                command = f"{FFMPEG} " \
                          f"-i {os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi " \
                          f"-c:v mpeg4 -vtag xvid -qscale:v 1 -c:a libmp3lame -qscale:a 1 " \
                          f"-filter_complex \"" \
                          f"[0:v]trim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_video_filter}setpts=PTS-STARTPTS[v0]; " \
                          f"[0:a]atrim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a0] " \
                          f"\" " \
                          f"-map \"[v0]\" -map \"[a0]\" " \
                          f" -y {os.path.join(self.qoemu_config.video_capture_path.get(), output_filename)}.avi"
            log.debug(f"postproc mp4 reencoded cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()

            # Additionally create a H.264 encoded .mp4 output file
            if initbuf_len > 0:
                command = f"{FFMPEG} -i {prefix_video_path} " \
                          f"-i {os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi  " \
                          f"-crf 4 -filter_complex \"" \
                          f"[0:v]trim=0:{initbuf_len},setpts=PTS-STARTPTS[v0]; " \
                          f"[0:a]atrim=0:{initbuf_len},{prefix_video_ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a0]; " \
                          f"[1:v]trim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_video_filter}setpts=PTS-STARTPTS[v1]; " \
                          f"[1:a]atrim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a1]; " \
                          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]\" " \
                          f"-map \"[outv]\" -map \"[outa]\" " \
                          f" -y {os.path.join(self.qoemu_config.video_capture_path.get(), output_filename)}.mp4"
            else:
                command = f"{FFMPEG} " \
                          f"-i {os.path.join(self.qoemu_config.video_capture_path.get(), input_filename)}.avi " \
                          f"-crf 4 " \
                          f"-filter_complex \"" \
                          f"[0:v]trim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_video_filter}setpts=PTS-STARTPTS[v0]; " \
                          f"[0:a]atrim={main_video_start_time}:{main_video_end_time}," \
                          f"{ffmpeg_audio_filter}asetpts=PTS-STARTPTS[a0] " \
                          f"\" " \
                          f"-map \"[v0]\" -map \"[a0]\" " \
                          f" -y {os.path.join(self.qoemu_config.video_capture_path.get(), output_filename)}.mp4"
            log.debug(f"postproc mp4 reencoded cmd: {command}")
            subprocess.run(shlex.split(command), stdout=subprocess.PIPE,
                           universal_newlines=True).check_returncode()


def main():
    p = PostProcessor(get_default_qoemu_config())
    p.process("VS-C-1_E1-R-0.1_P0", "test", 2, 5, 10, normalize_audio=True, erase_box=[2180, 930, 130, 130])

    print("Done.")


if __name__ == '__main__':
    main()
