#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""
from qoemu_pkg.analysis import analysis
from qoemu_pkg.capture.capture import CaptureEmulator,CaptureRealDevice
from qoemu_pkg.configuration import emulator_type, video_capture_path, traffic_analysis_live, traffic_analysis_plot, adb_device_serial
from qoemu_pkg.emulator.mobiledevice import MobileDeviceType, MobileDeviceOrientation
from qoemu_pkg.emulator.genymotion_emulator import GenymotionEmulator
from qoemu_pkg.emulator.standard_emulator import StandardEmulator
from qoemu_pkg.emulator.physical_device import PhysicalDevice
from qoemu_pkg.netem.netem import Connection
from qoemu_pkg.uicontrol.uicontrol import UiControl
from qoemu_pkg.uicontrol.usecase import UseCaseType
from qoemu_pkg.parser.parser import *


import logging as log
import threading
import time
import sys
import traceback

NET_DEVICE_NAME = "enp0s31f6"             # TODO: get from config file
COORDINATOR_RELEASE = "0.1"

GEN_LOG_FILE = os.path.join(video_capture_path, 'qoemu.log')


def wait_countdown(time_in_sec: int):
    for i in range(time_in_sec):
        sys.stdout.write(f"\rWaiting: {time_in_sec - i} s")
        time.sleep(1)
        sys.stdout.flush()
    sys.stdout.write("\r                                              \n")


def convert_to_seconds(time_str: str)->float:
    ts = time.strptime(time_str, "%H:%M:%S")
    s = ts.tm_hour * 3600 + ts.tm_min * 60 + ts.tm_sec
    return s

class Coordinator:
    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.ui_control = UiControl(adb_device_serial)
        if emulator_type == MobileDeviceType.GENYMOTION:
            self.emulator = GenymotionEmulator()
            self.capture = CaptureEmulator()
        if emulator_type == MobileDeviceType.SDK_EMULATOR:
            self.emulator = StandardEmulator()
            self.capture = CaptureEmulator()
        if emulator_type == MobileDeviceType.REAL_DEVICE:
            self.emulator = PhysicalDevice()
            self.capture = CaptureRealDevice()

        if not self.emulator:
            raise RuntimeError('No emulation device configured - check you \"qoemu.conf\" .')
        self._is_prepared = False
        self.netem = None
        self.analysis = None
        self.output_filename = None
        self._gen_log = open(GEN_LOG_FILE, "a+")

    def _get_video_id(self, type_id: str, table_id: str, entry_id: str) -> str:
        emulator_id = "E1-"
        if emulator_type == MobileDeviceType.SDK_EMULATOR:
            emulator_id += "S"
        if emulator_type == MobileDeviceType.GENYMOTION:
            emulator_id += "G"
        if emulator_type == MobileDeviceType.REAL_DEVICE:
            emulator_id += "R"

        emulator_id += f"-{COORDINATOR_RELEASE}"

        id = f"{type_id}-{table_id}-{entry_id}_{emulator_id}_P0"
        return id

    def _get_bpf_rule(self) -> str:
        if self.netem.android_ip:
            return f"host {self.netem.android_ip}"
        raise RuntimeError("check port rule")
        # TODO: return valid bpf rule which excludes the exclude_ports
        if self.netem.exclude_ports:
            return f" "


    def prepare(self, type_id: str, table_id: str, entry_id: str):
        params = get_parameters(type_id, table_id, entry_id)
        log.debug(f"Preparing with parameters: {params}")
        self.output_filename = self._get_video_id(type_id, table_id, entry_id)
        time_string = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
        self._gen_log.write(f"{time_string} {self.output_filename} {params} ")

        # self.emulator.delete_vd()  # delete/reset virtual device - should be avoided if use-case requires play services
        self.emulator.launch(orientation=MobileDeviceOrientation.LANDSCAPE)
        # [t_init, rul, rdl, dul, ddl]
        try:
            delay_bias_ul_dl = self.emulator.measure_rtt() / 2    # can only measure RTT, assume 50%/50% ul vs. dl
        except RuntimeError as rte:
            self._gen_log.write(f" measuring delay bias failed - canceled. ")
            log.error(" measuring delay bias failed - check if you have Internet connectivity!")
            raise rte
        if delay_bias_ul_dl > params['dul'] or delay_bias_ul_dl > params['ddl']:
            self._gen_log.write(f" delay bias of {delay_bias_ul_dl}ms too high - canceled. ")
            raise RuntimeError(f"Delay bias of {delay_bias_ul_dl}ms exceeds delay parameter of {params['ddl']}ms! Cannot emulate.")

        self.netem = Connection("coord1", NET_DEVICE_NAME, t_init=params['t_init'],
                                rul=params['rul'], rdl=params['rdl'],
                                dul=(params['dul']-delay_bias_ul_dl),
                                ddl=(params['ddl']-delay_bias_ul_dl),
                                exclude_ports=[22, 5000, 5002])  # exclude ports used for nomachine/ssh remote control
        # android_ip=self.emulator.get_ip_address())
        # set and execute a Youtube use case
        # Tagesschau Intro:
        # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/5lEd5D2J27Y?t=8")
        # Beethoven

        # append ?t=[start time in seconds] to link and create use-case
        s = convert_to_seconds(get_start(type_id, table_id, entry_id))
        url = f"{get_link(type_id, table_id, entry_id)}"
        if len(url) < 7:
            raise RuntimeError(f"Invalid Url: {url}")
        if "?" in url:
            url = f"{url}&t={s}"
        else:
            url = f"{url}?t={s}"
        self.ui_control.set_use_case(UseCaseType.YOUTUBE, url=url)
        self._gen_log.write(f"delay bias: {delay_bias_ul_dl}ms; video url: {url}; len: {s}s ")
        self.ui_control.prepare_use_case()
        self._gen_log.flush()
        self._is_prepared = True

    def execute(self, capture_time:str='00:00:30'):
        if not self._is_prepared:
            log.error("Cannot execute campaign - not prepared.")
            return

        # initialize traffic analysis - if enabled
        if traffic_analysis_live or traffic_analysis_plot:
            length_in_sec = convert_to_seconds(capture_time)
            self.analysis = analysis.DataCollector(self.netem.virtual_device_in, self.netem.virtual_device_in,
                                                   10, length_in_sec, bpf_filter=self._get_bpf_rule())
            self.analysis.start_threads()
            self.analysis.start()

        # execute concurrently in separate threads
        uc_duration = convert_to_seconds(capture_time) + 2  # add 2s safety margin
        ui_control_thread = threading.Thread(target=self.ui_control.execute_use_case, args=(uc_duration,))
        capture_thread = threading.Thread(target=self.capture.start_recording, args=(self.output_filename, capture_time))
        self.netem.enable_netem()
        ui_control_thread.start()
        capture_thread.start()
        capture_thread.join()
        ui_control_thread.join()
        self.netem.disable_netem()

    def finish(self):
        if not self._is_prepared:
            log.warning("finish called for a campaign which is not prepared")
        if self._gen_log:
            timestring = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
            self._gen_log.write(f" finished at {timestring}\r\n")
            self._gen_log.close()
            self._gen_log = None
        if self.netem:
            self.netem.cleanup()
            self.netem = None
        if self.ui_control:
            try:
                self.ui_control.shutdown_use_case()
            except RuntimeError as rte:
                log.error(f"exception during ui shutdown: {rte}")
        if self.emulator:
            self.emulator.shutdown()


if __name__ == '__main__':
    # executed directly as a script
    print("Coordinator main started")
    load_parameter_file('../stimuli-params/full.csv')
    print(get_type_ids())
    print(get_table_ids('VS'))
    print(get_entry_ids('VS', 'B'))

#    print(get_link('VS', 'A', '1'))
#    print(get_start('VS', 'A', '1'))
#    print(get_end('VS', 'A', '1'))

    ids_to_evaluate = get_entry_ids('VS', 'B')

    try:
        # for id in ids_to_evaluate:
        for id in ['6']:#,'5','4','3','2','1']:
            coordinator = Coordinator()
            try:
                coordinator.prepare('VS', 'B', id)
                wait_countdown(2)
                coordinator.execute('00:03:00')
                wait_countdown(5)
            finally:
                coordinator.finish()
    except RuntimeError as err:
        traceback.print_exc()
        print("******************************************************************************************************")
        print(f"RuntimeError occured: {err}")
        print(f"Coordinated QoEmu run canceled.")
        print("******************************************************************************************************")

    print("Done.")
