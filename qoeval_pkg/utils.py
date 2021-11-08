# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
import os
import sys
import time
from datetime import datetime
from typing import List

from qoeval_pkg.configuration import QoEvalConfiguration, MobileDeviceType
from . import __version__
from .parser.parser import get_entry_ids, get_parameters, get_codec


def wait_countdown(time_in_sec: int):
    for i in range(time_in_sec):
        sys.stdout.write(f"\rWaiting: {time_in_sec - i} s")
        time.sleep(1)
        sys.stdout.flush()
    sys.stdout.write("\r                                              \n")


def convert_to_seconds(time_str: str) -> float:
    if "." in time_str:
        ts = datetime.strptime(time_str, "%H:%M:%S.%f")
    else:
        ts = datetime.strptime(time_str, "%H:%M:%S")
    s = ts.hour * 3600 + ts.minute * 60 + ts.second + (ts.microsecond / 1000000.0)
    return s


def convert_to_timestr(time_in_seconds: float) -> str:
    hours = int(time_in_seconds / 3600)
    minutes = int((time_in_seconds - (3600 * hours)) / 60)
    seconds = int((time_in_seconds - (3600 * hours) - (60 * minutes)))
    ms = int(((time_in_seconds - (3600 * hours) - (60 * minutes)) - seconds) * 1000)
    return f"{hours}:{minutes}:{seconds}.{ms:03d}"


def get_video_id(qoeval_config: QoEvalConfiguration, type_id: str, table_id: str, entry_id: str,
                 postprocessing_step: str = "0") -> str:
    emulator_id = "E1-"
    if qoeval_config.emulator_type.get() == MobileDeviceType.SDK_EMULATOR:
        emulator_id += "S"
    if qoeval_config.emulator_type.get() == MobileDeviceType.GENYMOTION:
        emulator_id += "G"
    if qoeval_config.emulator_type.get() == MobileDeviceType.REAL_DEVICE:
        emulator_id += "R"

    emulator_id += f"-{__version__}"

    id = f"{type_id}-{table_id}-{entry_id}_{emulator_id}_P{postprocessing_step}"
    return id


def get_stimuli_filename(qoeval_config: QoEvalConfiguration, type_id, table_id, entry_id,
                         postprocessing_step: str = "0") -> str:
    return f"{get_video_id(qoeval_config, type_id, table_id, entry_id, postprocessing_step)}.avi"


def is_stimuli_available(qoeval_config: QoEvalConfiguration, type_id, table_id, entry_id,
                         postprocessing_step: str = "0") -> bool:
    filename = get_stimuli_filename(qoeval_config, type_id, table_id, entry_id, postprocessing_step)
    filepath = os.path.join(qoeval_config.video_capture_path.get(), filename)
    return os.path.isfile(filepath)


# Compare only relevant parts of two parameter sets to determine if these are alternative parameter sets
# Note: Which parameters are relevant can depend on the type of the stimuli, since e.g. for
#       Video Stream With Generated Buffering (VSB) the t_init parameter is only relevant for post-processing step 2
def are_alternative_params(params_A, params_B, type_id, postprocessing_step):
    checklist = ['rul', 'rdl', 'dul', 'ddl', 'codec', 'dynamic']
    if not ( type_id == "VSB" and postprocessing_step in ["0", "1"] ):
        checklist.append('t_init')
    is_ok = True
    for check in checklist:
        is_ok = is_ok and params_A[check] == params_B[check]
    return is_ok


def get_existing_stimuli_with_same_parameters(qoeval_config: QoEvalConfiguration, type_id, table_id, entry_id,
                                              postprocessing_step) -> List[str]:
    stimuli = []

    ids_available = get_entry_ids(type_id, table_id)
    desired_params = get_parameters(type_id, table_id, entry_id)
    desired_codec = get_codec(type_id, table_id, entry_id)

    for entry_id_to_check in ids_available:
        params = get_parameters(type_id, table_id, entry_id_to_check)
        if are_alternative_params(params, desired_params, type_id, postprocessing_step) and \
                is_stimuli_available(qoeval_config, type_id, table_id, entry_id_to_check, postprocessing_step):
            path_to_stimuli = os.path.join(qoeval_config.video_capture_path.get(),
                                           get_stimuli_filename(qoeval_config, type_id, table_id, entry_id_to_check,
                                                                postprocessing_step))
            stimuli.append(path_to_stimuli)

    return stimuli


def get_stimuli_path(qoeval_config: QoEvalConfiguration, type_id, table_id, entry_id,
                     postprocessing_step: str = "0",
                     reuse_existing_with_same_parameters=True) -> str:
    if is_stimuli_available(qoeval_config, type_id, table_id, entry_id, postprocessing_step):
        return os.path.join(qoeval_config.video_capture_path.get(),
                            get_stimuli_filename(qoeval_config, type_id, table_id, entry_id, postprocessing_step))

    if reuse_existing_with_same_parameters:
        stimuli = get_existing_stimuli_with_same_parameters(qoeval_config, type_id, table_id,
                                                            entry_id, postprocessing_step)
        if stimuli and len(stimuli) > 0:
            return stimuli[0]

    return None
