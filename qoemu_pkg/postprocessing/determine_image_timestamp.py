import io
import multiprocessing
import re
import subprocess
import cv2
import numpy as np


def frame_to_time(video_path, frame_number: int) -> float:
    """
    Converts a frame number to a timestamp of a given video

    :param video_path: the filepath to the video
    :param frame_number: the number of the frame to which the timestamp should be returned
    :return: the time of the frame as float
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

    counter = 0

    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        # file.write(line + '\n')
        if line.lstrip().startswith('<frame key_frame'):
            counter += 1
            if counter == frame_number:
                proc.terminate()
                return float(re.search(r'\bpkt_pts_time="(.+?)"', line).group(1))


def determine_frame(video_path: str, image_path: str) -> int:
    """
    Determines the timestamp of an image within a video. Has been tested with direct screenshots of the video,
    across different resulutions/video qualities.

    Analyzes all frames and picks the best fit.

    :param video_path: absolute path of the video
    :param image_path: absolute path of the image/screenshot
    :return: the frame of the video that fits best to the image
    """
    # reference image (grayscale)
    ref = cv2.imread(image_path, 0)

    if ref is None:
        raise RuntimeError(
            f"Cannot read trigger image {image_path}")

    # video capture from file
    cap = cv2.VideoCapture(video_path)

    if cap is None:
        raise RuntimeError(
            f"Cannot read video file {video_path}")

    black_and_white_level_max = 0
    frame_count = -1
    res = None
    while True:

        ret, frame = cap.read()

        # if we have a next frame
        if ret:
            frame_count += 1

            # convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff_frame = gray - ref

            # create mask to compare at full resolution
            mask = np.zeros(ref.shape[:2], np.uint8)
            mask[0:1080, 0:1920] = 255

            # calculate histogram
            hist = cv2.calcHist([diff_frame], [0], mask, [256], [0, 256])

            # compare black and white levels
            black_and_white_level = sum(int(e[0]) for e in hist[0:15]) + sum(int(e[0]) for e in hist[-16:])

            if black_and_white_level > black_and_white_level_max:
                res = frame_count
                black_and_white_level_max = black_and_white_level

        else:
            break

    cap.release()

    return res


if __name__ == '__main__':

    video_path = '/home/jk/PycharmProjects/qoemu/qoemu_pkg/gui/210418_VS-B/VS-B-6_E1-R-0.1_P0.avi'
    image_path = '/home/jk/PycharmProjects/qoemu/qoemu_pkg/gui/210418_VS-B/screen13.png'

    frame = determine_frame(video_path, image_path)
    print(frame)
    print(frame_to_time(video_path, frame))
