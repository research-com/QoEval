#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""
from qoemu_pkg.analysis import analysis
from qoemu_pkg.capture.capture import CaptureEmulator,CaptureRealDevice,PostProcessor
from qoemu_pkg.configuration import emulator_type, video_capture_path, traffic_analysis_live, \
    traffic_analysis_plot, adb_device_serial, net_device_name, net_em_sanity_check
from qoemu_pkg.configuration import MobileDeviceType, MobileDeviceOrientation
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

COORDINATOR_RELEASE = "0.1"
DELAY_TOLERANCE_MIN = 5     # minimum delay tolerance for sanity check [ms]
DELAY_TOLERANCE_REL = 0.05  # relative delay tolerance for sanity check [0..1]
PROCESSING_BIAS = 10        # additionaly delay due to processing in emulator [ms]

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

def get_video_id(type_id: str, table_id: str, entry_id: str, postprocessing_step: str = "0") -> str:
        emulator_id = "E1-"
        if emulator_type == MobileDeviceType.SDK_EMULATOR:
            emulator_id += "S"
        if emulator_type == MobileDeviceType.GENYMOTION:
            emulator_id += "G"
        if emulator_type == MobileDeviceType.REAL_DEVICE:
            emulator_id += "R"

        emulator_id += f"-{COORDINATOR_RELEASE}"

        id = f"{type_id}-{table_id}-{entry_id}_{emulator_id}_P{postprocessing_step}"
        return id

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
        self.stats_filepath = None
        self._gen_log = open(GEN_LOG_FILE, "a+")

    def _get_bpf_rule(self) -> str:
        filter_rule = ""
        if self.netem.android_ip:
            filter_rule = f"host {self.netem.android_ip}"
        for p in self.netem.exclude_ports:
            if(len(filter_rule)>0):
                filter_rule = f"{filter_rule} && "
            filter_rule = f"{filter_rule} !(tcp port {p}) && !(udp port {p})"
        log.debug(f"_get_bpf_rule filter rule: {filter_rule}")
        return filter_rule


    def prepare(self, type_id: str, table_id: str, entry_id: str):
        params = get_parameters(type_id, table_id, entry_id)
        log.debug(f"Preparing with parameters: {params}")
        self.output_filename = get_video_id(type_id, table_id, entry_id)
        time_string = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
        self._gen_log.write(f"{time_string} {self.output_filename} {params} ")

        # self.emulator.delete_vd()  # delete/reset virtual device - should be avoided if use-case requires play services
        self.emulator.launch(orientation=MobileDeviceOrientation.LANDSCAPE)
        # [t_init, rul, rdl, dul, ddl]
        try:
            delay_bias_ul_dl = (self.emulator.measure_rtt()+PROCESSING_BIAS) / 2    # can only measure RTT, assume 50%/50% ul vs. dl
        except RuntimeError as rte:
            self._gen_log.write(f" measuring delay bias failed - canceled. ")
            log.error(" measuring delay bias failed - check if you have Internet connectivity!")
            raise rte
        if delay_bias_ul_dl > params['dul'] or delay_bias_ul_dl > params['ddl']:
            self._gen_log.write(f" delay bias of {delay_bias_ul_dl}ms too high - canceled. ")
            raise RuntimeError(f"Delay bias of {delay_bias_ul_dl}ms exceeds delay parameter of {params['ddl']}ms! Cannot emulate.")

        self.netem = Connection("coord1", net_device_name, t_init=params['t_init'],
                                rul=params['rul'], rdl=params['rdl'],
                                dul=(params['dul']-delay_bias_ul_dl),
                                ddl=(params['ddl']-delay_bias_ul_dl),
                                # cannot use mobile dev ip in hostap mode android_ip=self.emulator.get_ip_address(),
                                exclude_ports=[22, 5000, 5002])  # exclude ports used for nomachine/ssh remote control

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

        # calculate approximate duration of use-case
        uc_duration = convert_to_seconds(capture_time) + 2  # add 2s safety margin

        # initialize traffic analysis - if enabled
        if traffic_analysis_live or traffic_analysis_plot:
            length_in_sec = convert_to_seconds(capture_time)
            self.stats_filepath = os.path.join(video_capture_path, f"{self.output_filename}_stats")
            self.analysis = analysis.DataCollector(self.netem.virtual_device_out, self.netem.virtual_device_in,
                                                   10, uc_duration, filename= self.stats_filepath,
                                                   bpf_filter=self._get_bpf_rule())
            self.analysis.start_threads()

        # optional sanity check (can be disbled in configuration file)
        if(net_em_sanity_check):
            self.netem.enable_netem(consider_t_init=False)
            log.debug("network emulation sanity check - measuring delay while emulation is active...")
            params = get_parameters(type_id, table_id, entry_id)
            measured_rtt_during_emulation = self.emulator.measure_rtt()
            max_allowed_rtt_during_emulation = params['dul'] + params['ddl'] + \
                                               max(DELAY_TOLERANCE_MIN, DELAY_TOLERANCE_REL*(params['dul'] + params['ddl'] ))
            self._gen_log.write(f" emu rtt: {measured_rtt_during_emulation}ms max rtt: {max_allowed_rtt_during_emulation}ms ")
            if measured_rtt_during_emulation > max_allowed_rtt_during_emulation:
                self._gen_log.write(f" network emulation sanity check failed - canceled. ")
                raise RuntimeError(f"Measured RTT of {measured_rtt_during_emulation}ms exceeds maximum allowed RTT of {max_allowed_rtt_during_emulation}ms! Sanity check failed.")

        # execute concurrently in separate threads
        ui_control_thread = threading.Thread(target=self.ui_control.execute_use_case, args=(uc_duration,))
        capture_thread = threading.Thread(target=self.capture.start_recording, args=(self.output_filename, capture_time))

        self.netem.enable_netem()
        # input("netem active - check conditions on mobile device and press enter to continue...")

        if traffic_analysis_live or traffic_analysis_plot:
            self.analysis.start()

        if traffic_analysis_live:
            live_plot = analysis.LivePlot(self.analysis, analysis.PACKETS, analysis.ALL)

        ui_control_thread.start()
        capture_thread.start()

        if traffic_analysis_live:
            log.debug("Showing live plot - close window to continue processing when use-case has finished.")
            live_plot.show()

        capture_thread.join()
        ui_control_thread.join()
        self.netem.disable_netem()

        if traffic_analysis_plot:
            self.analysis.wait_until_completed()
            plot = analysis.Plot(self.stats_filepath,0,convert_to_seconds(capture_time),analysis.BYTES,
                                 [analysis.OUT],[analysis.ALL],analysis.BAR)
            plot.save_pdf(f"{self.stats_filepath}_out")
            plot.save_png(f"{self.stats_filepath}_out")
            plot = analysis.Plot(self.stats_filepath, 0, convert_to_seconds(capture_time),analysis.BYTES,
                                 [analysis.IN],[analysis.ALL],analysis.BAR)
            plot.save_pdf(f"{self.stats_filepath}_in")
            plot.save_png(f"{self.stats_filepath}_in")


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

    do_generate_stimuli = True
    do_postprocessing = False

#    print(get_link('VS', 'A', '1'))
#    print(get_start('VS', 'A', '1'))
#    print(get_end('VS', 'A', '1'))

    type_id = 'VS'
    table_id = 'B'
    ids_to_evaluate = get_entry_ids(type_id, table_id)
    # ids_to_evaluate =  ['6'] #,'5','4','3','2','1']

    try:
        if do_generate_stimuli:
                for entry_id in ids_to_evaluate:
                    try:
                        coordinator = Coordinator()
                        coordinator.prepare(type_id, table_id, entry_id)
                        wait_countdown(2)
                        coordinator.execute('00:00:20')
                        wait_countdown(5)
                    finally:
                        coordinator.finish()

        if do_postprocessing:
            print ("Semi-manual post-processing starts... ")
            print ("Please use a video player of your choice to answer the following questions.")
            print("")
            for entry_id in ids_to_evaluate:
                video_id_in  = get_video_id(type_id, table_id, entry_id,"0")
                video_id_out = get_video_id(type_id, table_id, entry_id,"1")
                postprocessor = PostProcessor()
                print(f"Processing: {video_id_in}")
                t_init_buf = str(
                    input(f"Time for until playback starts (T_init + time to fill playback buffer) [hh:mm:ss.xxx]: "))
                t_raw_start = str(input(f"Time when relevant section starts in raw stimuli video [hh:mm:ss.xxx]: "))
                postprocessor.process(video_id_in, video_id_out, t_init_buf, t_raw_start)
                print(f"Finished post-processing: {video_id_in} ==> {video_id_out}")

    except RuntimeError as err:
            traceback.print_exc()
            print("******************************************************************************************************")
            print(f"RuntimeError occured: {err}")
            print(f"Coordinated QoEmu run canceled.")
            print("******************************************************************************************************")


    print("Done.")
