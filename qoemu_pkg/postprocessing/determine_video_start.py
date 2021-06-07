import io
import multiprocessing
import subprocess
import re


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

    prediction = None
    counter = 0
    countdown = -1

    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):

        if line.lstrip().startswith('<frame key_frame'):
            key = bool(int(re.search(r'\bkey_frame="(.+?)"', line).group(1)))
            time = float(re.search(r'\bpkt_pts_time="(.+?)"', line).group(1))
            size = int(re.search(r'\bpkt_size="(.+?)"', line).group(1))

            # size of differential frame that triggers start of video
            threshold = 40000
            # number of frames needed above the threshold to avoid false positives
            threshold_frames_needed = 20
            # allow the frame size to dip below the threshold this many times to avoid false negatives
            lower_frames_allowed = 20

            if not key:
                if size > threshold:
                    if counter == threshold_frames_needed:
                        proc.terminate()
                        return prediction
                    if counter > 0:
                        counter += 1
                    if counter == 0:
                        prediction = time
                        counter = 1
                        countdown = lower_frames_allowed
                else:
                    if countdown == 0:
                        countdown = -1
                        counter = 0
                    if countdown > 0:
                        countdown -= 1

    proc.terminate()
    return None


if __name__ == '__main__':

    video_path = '/home/jk/PycharmProjects/qoemu/qoemu_pkg/gui/210418_VS-B/test3.avi'

    print(determine_video_start(video_path))
