import os
from datetime import datetime
import sys
import time

from qoemu_pkg.configuration import config, MobileDeviceType

QOE_RELEASE = "0.1"

def wait_countdown(time_in_sec: int):
    for i in range(time_in_sec):
        sys.stdout.write(f"\rWaiting: {time_in_sec - i} s")
        time.sleep(1)
        sys.stdout.flush()
    sys.stdout.write("\r                                              \n")

def convert_to_seconds(time_str: str)->float:
    if "." in time_str:
        ts = datetime.strptime(time_str, "%H:%M:%S.%f")
    else:
        ts = datetime.strptime(time_str, "%H:%M:%S")
    s = ts.hour * 3600 + ts.minute * 60 + ts.second + (ts.microsecond / 1000000.0)
    return s

def convert_to_timestr(time_in_seconds: float)->str:
    hours = int(time_in_seconds/3600)
    minutes = int((time_in_seconds - (3600*hours))/60)
    seconds = int((time_in_seconds - (3600*hours) - (60*minutes)))
    ms = int(((time_in_seconds - (3600*hours) - (60*minutes)) - seconds)*1000)
    return f"{hours}:{minutes}:{seconds}.{ms}"

def get_video_id(type_id: str, table_id: str, entry_id: str, postprocessing_step: str = "0") -> str:
    emulator_id = "E1-"
    if config.emulator_type.get() == MobileDeviceType.SDK_EMULATOR:
        emulator_id += "S"
    if config.emulator_type.get() == MobileDeviceType.GENYMOTION:
        emulator_id += "G"
    if config.emulator_type.get() == MobileDeviceType.REAL_DEVICE:
        emulator_id += "R"

    emulator_id += f"-{QOE_RELEASE}"

    id = f"{type_id}-{table_id}-{entry_id}_{emulator_id}_P{postprocessing_step}"
    return id

def is_stimuli_available(type_id, table_id, entry_id, postprocessing_step: str = "0"):
    filename = f"{get_video_id(type_id, table_id, entry_id, postprocessing_step)}.avi"
    filepath = os.path.join(config.video_capture_path.get(), filename)
    return os.path.isfile(filepath)