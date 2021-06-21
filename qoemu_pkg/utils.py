from datetime import datetime
import sys
import time


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