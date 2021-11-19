# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
import os
import shlex
import subprocess

import importlib_resources
import logging as log

from qoeval_pkg.configuration import QoEvalConfiguration
from qoeval_pkg.parser.parser import get_parameters
from qoeval_pkg.postprocessing.bufferer.bufferer import Bufferer
from qoeval_pkg.postprocessing.postprocessor import FFPROBE
from qoeval_pkg.utils import get_stimuli_path, get_video_id
from qoeval_pkg import spinner

FFMPEG = "ffmpeg"
_SPINNER_NAME = "spinner-thin-line-200-trans.png"


def _get_video_duration(input_path: str):
    command = f"{FFPROBE} -v error -select_streams v:0 -show_entries format=duration " \
              f"-of default=noprint_wrappers=1:nokey=1 " \
              f"{input_path}"
    output = subprocess.run(shlex.split(command), stdout=subprocess.PIPE, universal_newlines=True)
    output.check_returncode()
    return float(output.stdout)


class BufferingGenerator:
    def __init__(self, qoeval_config: QoEvalConfiguration):
        self.qoeval_config = qoeval_config
        self._spinner = importlib_resources.files(spinner) / _SPINNER_NAME

    def generate(self, type_id, table_id, entry_id):

        input_path = get_stimuli_path(self.qoeval_config, type_id, table_id, entry_id, "1", True)
        if not os.path.isfile(input_path):
            log.error(f"Cannot open post-processed input file {input_path}")
            raise RuntimeError(f"Video file {input_path} does not exist.")

        output_path = os.path.join(self.qoeval_config.video_capture_path.get(),
                                   get_video_id(self.qoeval_config, type_id, table_id, entry_id, "2") + ".avi")

        params = get_parameters(type_id, table_id, entry_id)

        buffering_list = ''
        if params['t_init'] > 0:
            duration = params['t_init']
            duration = duration / 1000.0  # t_init is in [ms]
            log.info(f"Adding artificial buffering time for t_init == {duration} s")
            buffering_list = f'[0, {duration}]'

        if params['genbufn'] > 0:
            n = int(params['genbufn'])
            video_duration = _get_video_duration(input_path)
            buffering_duration = params['genbuft'] / 1000.0  # parameter is in [ms]
            log.info(f"Adding {n} artificial buffering times of {buffering_duration}s "
                     f"to video with total length of {video_duration}s")
            delta = video_duration / (n + 1)
            if len(buffering_list) > 0:
                buffering_list = f'{buffering_list},'
            for i in range(n):
                buffering_list = f'{buffering_list} [{delta * (i + 1)}, {buffering_duration}]'
                if i < (n-1):
                    buffering_list = f'{buffering_list},'

        log.info(f"Generating artificial buffering: {buffering_list}")

        if len(buffering_list) < 4:
            log.error(f"Cannot generate buffering phases - list of buffering times is empty.")
            return

        with importlib_resources.as_file(self._spinner) as spinner_path:
            buffer_args = {'--input': f'{input_path}',
                           '--output': f'{output_path}',
                           '--spinner': f'{spinner_path}',
                           '--buflist': f'{buffering_list}',
                           '--disable-spinner': False,
                           '--speed': 1.0,
                           '--trim': None,
                           '--force': False,
                           '--dry-run': False,
                           '--vcodec': 'mpeg4',
                           '--acodec': 'libmp3lame',
                           '--pixfmt': 'yuv420p',
                           '--verbose': True,
                           '--brightness': 0.0,
                           '--blur': 1,
                           '--audio-disable': False,
                           '--black-frame': True,
                           '--force-framerate': False,
                           '--skipping': False}
            bufferer = Bufferer(buffer_args)
            try:
                bufferer.insert_buf_audiovisual()
            except Exception as e:
                raise RuntimeError("generating buffer video failed: " + str(e))

    def recode_setpts(self, type_id, table_id, entry_id):
        input_path = get_stimuli_path(self.qoeval_config, type_id, table_id, entry_id, "2", True)
        if not os.path.isfile(input_path):
            log.error(f"Cannot open post-processed input file {input_path}")
            raise RuntimeError(f"Video file {input_path} does not exist.")

        output_path = os.path.join(self.qoeval_config.video_capture_path.get(),
                                   get_video_id(self.qoeval_config, type_id, table_id, entry_id, "3") + ".avi")

        log.info(f"Recoding {input_path} to {output_path} (with PTS starting at zero)...")

        command = f"{FFMPEG} -i {input_path} -c:v mpeg4 -vtag xvid -qscale:v 1 -c:a libmp3lame -qscale:a 1 " \
                  f"-filter_complex \"[0:v]setpts=PTS-STARTPTS[v0];[0:a]asetpts=PTS-STARTPTS[a0]\" " \
                  f"-map \"[v0]\" -map \"[a0]\" -y " \
                  f" {output_path}"

        output = subprocess.run(shlex.split(command), stderr=subprocess.PIPE,
                                universal_newlines=True)
        output.check_returncode()
