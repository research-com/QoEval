# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#           Jan Andreas Krahl <krahl.jan@hm.edu>
#
# License:  LGPL 3.0 - see LICENSE file for details
import io
import multiprocessing
import subprocess
import re
import logging as log
from qoeval_pkg.configuration import QoEvalConfiguration


def determine_video_start(qoeval_config: QoEvalConfiguration, video_path: str, minimum_start_time: float = 0.0) -> float:
    """

    :param qoeval_config:  The qoevalConfiguration providing threshold values
    :param video_path: the absolute path to the video
    :param minimum_start_time: minimum value (to avoid misdetection before known minimum start time)
    :return: the determined playback start of the video as float, None if the algorithm fails to determine it
    """
    cpu_count = multiprocessing.cpu_count()

    proc = subprocess.Popen(['ffprobe', '-hide_banner', '-show_frames',
                             '-show_streams',
                             '-threads', str(cpu_count),
                             '-loglevel', 'quiet',
                             '-show_entries', 'frame=key_frame,pkt_size,pkt_pts_time',
                             '-print_format', 'xml',
                             '-select_streams', 'v:0',
                             video_path], stdout=subprocess.PIPE)

    # config parameters (must be read upon each call since they can change over time)
    #   size [B] of differential frame that triggers start of video (normal relevance)
    DIFF_THRESHOLD_SIZE_NORMAL_RELEVANCE = qoeval_config.vid_start_detect_thr_size_normal_relevance.get()
    #   size [B] of differential frame that triggers start of video (high relevance, strong indicator)
    DIFF_THRESHOLD_SIZE_HIGH_RELEVANCE = qoeval_config.vid_start_detect_thr_size_high_relevance.get()
    #   number of frames needed above the threshold to avoid false positives
    DIFF_THRESHOLD_NR_FRAMES = qoeval_config.vid_start_detect_thr_nr_frames.get()

    # allow the frame size to dip below the threshold this many times to avoid false negatives
    DIFF_THRESHOLD_LOWER_FRAMES_ALLOWED = 7
    # assumed accuracy for time [s] - times less then TIME_ACCURARY apart will be considered identical
    TIME_ACCURACY = 0.001

    # currently predicted start time
    prediction = None
    # number of differential frames observed which indicate a started video
    counter_positive = 0
    # remaining number of tolerated diffenential frames observed indicating an not-started video
    remaining_tolerated = -1

    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):

        if line.lstrip().startswith('<frame key_frame'):
            # log.debug(line)
            key = bool(int(re.search(r'\bkey_frame="(.+?)"', line).group(1)))
            time = float(re.search(r'\bpkt_pts_time="(.+?)"', line).group(1))
            size = int(re.search(r'\bpkt_size="(.+?)"', line).group(1))

            if time < minimum_start_time:
                continue

            if not key:
                log.debug(f"time: {time}  size:{size}  counter: {counter_positive}  countdown: {remaining_tolerated}")
                if size > DIFF_THRESHOLD_SIZE_NORMAL_RELEVANCE:
                    if size > DIFF_THRESHOLD_SIZE_HIGH_RELEVANCE:
                        increment = 3
                    else:
                        increment = 1
                    if counter_positive > 0:
                        counter_positive += increment
                    if counter_positive == 0:
                        # found a new possible start time
                        prediction = time
                        counter_positive = increment
                        remaining_tolerated = DIFF_THRESHOLD_LOWER_FRAMES_ALLOWED
                    if counter_positive >= DIFF_THRESHOLD_NR_FRAMES:
                        # prediction seems to be a valid start time - stop searching
                        break
                else:
                    if remaining_tolerated == 0:
                        remaining_tolerated = -1
                        counter_positive = 0
                    if remaining_tolerated > 0:
                        remaining_tolerated -= 1

    proc.terminate()

    if prediction is None:
        raise RuntimeError(f"Failed to detect video start time - check threshold parameters for {video_path}")

    if abs(minimum_start_time-prediction) < TIME_ACCURACY:
        raise RuntimeError(f"Detected start time is identical to minimum start time. "
                           f"Video might already be started at time {minimum_start_time} or parameters "
                           f"for start detection in {video_path} are not set correctly.")

    return prediction
