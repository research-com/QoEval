import io
import multiprocessing
import subprocess
import re

# size [B] of differential frame that triggers start of video (normal relevance)
DIFF_THRESHOLD_SIZE_NORMAL_RELEVANCE = 20000
# size [B] of differential frame that triggers start of video (high relevance, strong indicator)
DIFF_THRESHOLD_SIZE_HIGH_RELEVANCE = 40000
# number of frames needed above the threshold to avoid false positives
DIFF_THRESHOLD_NR_FRAMES = 7
# allow the frame size to dip below the threshold this many times to avoid false negatives
DIFF_THRESHOLD_LOWER_FRAMES_ALLOWED = 4


def determine_video_start(video_path: str) -> float:
    """

    :param video_path: the absolute path to the video
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

    # currently predicted start time
    prediction = None
    # number of differential frames observed which indicate a started video
    counter_positive = 0
    # remaining number of tolerated diffenential frames observed indicating an not-started video
    remaining_tolerated = -1

    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):

        if line.lstrip().startswith('<frame key_frame'):
            # print(line)
            key = bool(int(re.search(r'\bkey_frame="(.+?)"', line).group(1)))
            time = float(re.search(r'\bpkt_pts_time="(.+?)"', line).group(1))
            size = int(re.search(r'\bpkt_size="(.+?)"', line).group(1))

            if not key:
                # print(f"counter: {counter_positive}  countdown: {remaining_tolerated}")
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
                        proc.terminate()
                        return prediction
                else:
                    if remaining_tolerated == 0:
                        remaining_tolerated = -1
                        counter_positive = 0
                    if remaining_tolerated > 0:
                        remaining_tolerated -= 1

    proc.terminate()
    return None


if __name__ == '__main__':

    video_path = '/home/jk/PycharmProjects/qoemu/qoemu_pkg/gui/210418_VS-B/test3.avi'

    print(determine_video_start(video_path))
