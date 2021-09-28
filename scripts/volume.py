#!/bin/python3
import argparse
import re
import shlex
import subprocess
from typing import List

FFMPEG = "ffmpeg"
HEADER = "file, maximum volume, mean volume, histogram_2db, histogram_3db, histogram_4db, histogram_5db, " \
         "histogram_6db, histogram_7db, histogram_8db"


def _get_volume_info(input_filename_list: List[str]) -> str:
    result = ""
    input_filename_list.sort()
    for input_filename in input_filename_list:
        command = f"{FFMPEG} -i {input_filename} -af \"volumedetect\" -vn -sn -dn -f null /dev/null "
        output = subprocess.run(shlex.split(command), stderr=subprocess.PIPE,
                                universal_newlines=True)
        output.check_returncode()
        pattern = r"\s*max_volume:\s(-?\d*\.?\d*)\sdB*"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stderr))
        if match:
            max_vol = float(match.group(1))
        else:
            raise RuntimeError('max_volume detection failed.')

        pattern = r"\s*mean_volume:\s(-?\d*\.?\d*)\sdB*"
        matcher = re.compile(pattern)
        match = (matcher.search(output.stderr))
        if match:
            mean_vol = float(match.group(1))
        else:
            raise RuntimeError('mean_volume detection failed.')

        hist_vol = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        hist_vol_str = ""

        for i in range(2,9):
            pattern = rf"\s*histogram_{i}db:\s(-?\d*\.?\d*)"
            matcher = re.compile(pattern)
            match = (matcher.search(output.stderr))
            if match:
                hist_vol[i] = int(match.group(1))
            # Note: since not all files report data for all bins, we ignore a non-match
            # else:
            #     print(output.stderr)
            #     raise RuntimeError('histogram_volume detection failed.')

            hist_vol_str = hist_vol_str + f"{hist_vol[i]}"
            if i < 8:
                hist_vol_str = hist_vol_str + ", "

        result = result + f"{input_filename}, {max_vol}, {mean_vol}, {hist_vol_str}\n"
    return result


parser = argparse.ArgumentParser()
parser.add_argument('inputfile', nargs='*', help='Specifies the path to the file to be evaluated, e.g. VSB-D-1_E1-R-0.5.0_P1.avi')

args = parser.parse_args()

if len(args.inputfile) < 1:
    print("Missing required argument!")
    parser.print_help()
else:
    #print(f"Evaluating {args.inputfile}")
    print(HEADER)
    print(_get_volume_info(args.inputfile))
