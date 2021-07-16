#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""
from qoemu_pkg.analysis import analysis
from qoemu_pkg.capture.capture import CaptureEmulator, CaptureRealDevice
from qoemu_pkg.postprocessing.postprocessor import PostProcessor
from qoemu_pkg.postprocessing.determine_video_start import determine_video_start
from qoemu_pkg.postprocessing.determine_image_timestamp import determine_frame, frame_to_time
from qoemu_pkg.configuration import MobileDeviceType, MobileDeviceOrientation, config
from qoemu_pkg.emulator.genymotion_emulator import GenymotionEmulator
from qoemu_pkg.emulator.standard_emulator import StandardEmulator
from qoemu_pkg.emulator.physical_device import PhysicalDevice
from qoemu_pkg.netem.netem import Connection
from qoemu_pkg.uicontrol.uicontrol import UiControl
from qoemu_pkg.uicontrol.usecase import UseCaseType
from qoemu_pkg.parser.parser import *
from qoemu_pkg.utils import *

import logging as log
import threading
import time
import traceback

from typing import List

DELAY_TOLERANCE_MIN = 10  # minimum delay tolerance for sanity check [ms]
DELAY_TOLERANCE_REL_NORMAL = 0.05  # relative delay tolerance for sanity check [0..1]
DELAY_TOLERANCE_REL_LOWBW = 0.25  # relative delay tolerance for sanity check in low-bandwidth conditions [0..1]
DELAY_MEASUREMENT_BW_THRESH = 100 # threshold data rate for sanity delay measurement [kbit/s]
PROCESSING_BIAS = 8  # additional delay due to processing in emulator [ms]
VIDEO_PRE_START = 1.0  # start video VIDEO_PRE_START [s] early so that we can guarantee to see the trigger
                       # Note: Be careful with VIDEO_PRE_START - if set too high, we might miss rebuffering
MAX_RETRIES = 2  # number of retries when generating a stimuli fails
SHORT_WAITING = 3  # short waiting time [s]
LONG_WAITING = 60  # long waiting time [s]

GEN_LOG_FILE = os.path.join(config.video_capture_path.get(), 'qoemu.log')


class Coordinator:
    """
            Coordinate the emulation run for generating one or more stimuli.
    """

    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.ui_control = UiControl(config.adb_device_serial.get())
        if config.emulator_type.get() == MobileDeviceType.GENYMOTION:
            self.emulator = GenymotionEmulator()
            self.capture = CaptureEmulator()
        if config.emulator_type.get() == MobileDeviceType.SDK_EMULATOR:
            self.emulator = StandardEmulator()
            self.capture = CaptureEmulator()
        if config.emulator_type.get() == MobileDeviceType.REAL_DEVICE:
            self.emulator = PhysicalDevice(config.show_device_screen_mirror.get())
            self.capture = CaptureRealDevice()

        if not self.emulator:
            raise RuntimeError('No emulation device configured - check you \"qoemu.conf\" .')
        self._is_prepared = False
        self.netem = None
        self.analysis = None
        self.output_filename = None
        self.stats_filepath = None
        self._type_id = None
        self._table_id = None
        self._entry_id = None

    def _get_bpf_rule(self) -> str:
        filter_rule = ""
        if self.netem.android_ip:
            filter_rule = f"host {self.netem.android_ip}"
        for p in self.netem.exclude_ports:
            if (len(filter_rule) > 0):
                filter_rule = f"{filter_rule} && "
            filter_rule = f"{filter_rule} !(tcp port {p}) && !(udp port {p})"
        log.debug(f"_get_bpf_rule filter rule: {filter_rule}")
        return filter_rule

    def _prepare(self, type_id: str, table_id: str, entry_id: str):
        if self._is_prepared:
            raise RuntimeError(
                f"Coordinator is already prepared - cannot prepare again before finish has been called.")

        self._gen_log = open(GEN_LOG_FILE, "a+")

        self._type_id = type_id
        self._table_id = table_id
        self._entry_id = entry_id
        self._params = get_parameters(self._type_id, self._table_id, self._entry_id)
        log.debug(f"Preparing {type_id}-{table_id}-{entry_id} with parameters: {self._params}")
        self.output_filename = get_video_id(self._type_id, self._table_id, self._entry_id)
        time_string = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
        self._gen_log.write(f"{time_string} {self.output_filename} {self._params} ")

        # self.emulator.delete_vd()  # delete/reset virtual device - should be avoided if use-case requires play services
        self.emulator.launch(orientation=MobileDeviceOrientation.LANDSCAPE)
        try:
            delay_bias_ul_dl = (
                                           self.emulator.measure_rtt() + PROCESSING_BIAS) / 2  # can only measure RTT, assume 50%/50% ul vs. dl
        except RuntimeError as rte:
            self._gen_log.write(f" measuring delay bias failed - canceled. ")
            log.error(" measuring delay bias failed - check if you have Internet connectivity!")
            raise rte
        if delay_bias_ul_dl > self._params['dul'] or delay_bias_ul_dl > self._params['ddl']:
            self._gen_log.write(f" delay bias of {delay_bias_ul_dl}ms too high - canceled. ")
            raise RuntimeError(
                f"Delay bias of {delay_bias_ul_dl}ms exceeds delay parameter of {self._params['ddl']}ms! Cannot emulate.")

        self.netem = Connection("coord1", config.net_device_name.get(), t_init=self._params['t_init'],
                                rul=self._params['rul'], rdl=self._params['rdl'],
                                dul=(self._params['dul'] - delay_bias_ul_dl),
                                ddl=(self._params['ddl'] - delay_bias_ul_dl),
                                android_ip=self.emulator.get_ip_address(),  # note: only valid, if not in host-ap mode
                                exclude_ports=config.excluded_ports.get())  # exclude ports, e.g. as used for ssh control

        url = f"{get_link(self._type_id, self._table_id, self._entry_id)}"
        if len(url) < 7:
            raise RuntimeError(f"Invalid Url: {url}")
        s = convert_to_seconds(get_start(self._type_id, self._table_id, self._entry_id))
        s = s - VIDEO_PRE_START
        if s > 0.0:
            # append ? or &t=[start time in seconds] to link (note: currently, youtube support only int values)
            if "?" in url:
                url = f"{url}&t={int(s)}"
            else:
                url = f"{url}?t={int(s)}"

        # create and prepare use-case
        self.ui_control.set_use_case(UseCaseType.YOUTUBE, url=url)
        self._gen_log.write(f"delay bias: {delay_bias_ul_dl}ms; video url: {url}; len: {s}s ")
        self.ui_control.prepare_use_case()
        self._gen_log.flush()
        self._is_prepared = True

    def _execute(self, capture_time: str = '00:00:30'):
        if not self._is_prepared:
            log.error("Cannot execute campaign - not prepared.")
            return

        # calculate approximate duration of use-case
        uc_duration = convert_to_seconds(capture_time) + 2  # add 2s safety margin

        # store a copy of the qoemu configuration used to generate the stimuli (to be reproducible)
        cfg_log = os.path.join(config.video_capture_path.get(), f"{self.output_filename}.cfg")
        config.save_to_file(cfg_log)

        # initialize traffic analysis - if enabled
        if config.traffic_analysis_live.get() or config.traffic_analysis_plot.get():
            self.stats_filepath = os.path.join(config.video_capture_path.get(), f"{self.output_filename}_stats")
            self.analysis = analysis.DataCollector(virtual_interface_out=self.netem.virtual_device_out,
                                                   virtual_interface_in=self.netem.virtual_device_in,
                                                   duration=uc_duration, interval=100, filename=self.stats_filepath,
                                                   bpf_filter=self._get_bpf_rule())
            self.analysis.start_threads()

        # optional sanity check (can be disbled in configuration file)
        if config.net_em_sanity_check.get():
            if self._params['rul'] < DELAY_MEASUREMENT_BW_THRESH or self._params['rdl']:
                log.warning("delay measurement in low-bandwidth situation - using higher relative tolerance")
                delay_tol_rel = DELAY_TOLERANCE_REL_LOWBW
            else:
                delay_tol_rel = DELAY_TOLERANCE_REL_NORMAL
            self.netem.enable_netem(consider_t_init=False)
            log.debug("network emulation sanity check - measuring delay while emulation is active...")
            measured_rtt_during_emulation = self.emulator.measure_rtt()
            max_allowed_rtt_during_emulation = self._params['dul'] + self._params['ddl'] + \
                                               max(DELAY_TOLERANCE_MIN,
                                                   delay_tol_rel * (self._params['dul'] + self._params['ddl']))
            self._gen_log.write(
                f" emu rtt: {measured_rtt_during_emulation}ms max rtt: {max_allowed_rtt_during_emulation}ms ")
            if measured_rtt_during_emulation > max_allowed_rtt_during_emulation:
                self._gen_log.write(f" network emulation sanity check failed - too high - canceled. ")
                raise RuntimeError(
                    f"Measured RTT of {measured_rtt_during_emulation}ms exceeds maximum allowed RTT of "
                    f"{max_allowed_rtt_during_emulation}ms! Sanity check failed.")
            if measured_rtt_during_emulation < self._params['dul'] + self._params['ddl']:
                self._gen_log.write(f" network emulation sanity check failed - too low - canceled. ")
                raise RuntimeError(
                    f"Measured RTT of {measured_rtt_during_emulation}ms is lower than the minimum allowed RTT of "
                    f"{self._params['dul'] + self._params['ddl']}ms! Sanity check failed.")

        # execute concurrently in separate threads
        ui_control_thread = threading.Thread(target=self.ui_control.execute_use_case, args=(uc_duration,))
        capture_thread = threading.Thread(target=self.capture.start_recording,
                                          args=(self.output_filename, capture_time))

        self.netem.enable_netem()
        # input("netem active - check conditions on mobile device and press enter to continue...")

        if config.traffic_analysis_live.get() or config.traffic_analysis_plot.get():
            self.analysis.start()

        if config.traffic_analysis_live.get():
            live_plot = analysis.LivePlot(self.analysis, analysis.PACKETS, analysis.ALL)

        ui_control_thread.start()
        capture_thread.start()

        if config.traffic_analysis_live.get():
            log.debug("Showing live plot - close window to continue processing when use-case has finished.")
            live_plot.show()

        capture_thread.join()
        ui_control_thread.join()

        if config.traffic_analysis_plot.get():
            self.analysis.wait_until_completed()
            plot = analysis.Plot(self.stats_filepath, 0, convert_to_seconds(capture_time), analysis.BYTES,
                                 [analysis.OUT], [analysis.ALL], analysis.BAR)
            plot.save_pdf(f"{self.stats_filepath}_out")
            plot.save_png(f"{self.stats_filepath}_out")
            plot = analysis.Plot(self.stats_filepath, 0, convert_to_seconds(capture_time), analysis.BYTES,
                                 [analysis.IN], [analysis.ALL], analysis.BAR)
            plot.save_pdf(f"{self.stats_filepath}_in")
            plot.save_png(f"{self.stats_filepath}_in")
            # TODO: bugfix histogram plots - currenlty, the visualized data frames are empty
            # plot = analysis.Plot(self.stats_filepath,0,convert_to_seconds(capture_time),analysis.BYTES,
            #                      [analysis.OUT],[analysis.ALL],analysis.HIST)
            # plot.save_pdf(f"{self.stats_filepath}_hist_out")
            # plot.save_png(f"{self.stats_filepath}_hist_out")
            # plot = analysis.Plot(self.stats_filepath, 0, convert_to_seconds(capture_time),analysis.BYTES,
            #                      [analysis.IN],[analysis.ALL],analysis.HIST)
            # plot.save_pdf(f"{self.stats_filepath}_hist_in")
            # plot.save_png(f"{self.stats_filepath}_hist_in")

        self.netem.disable_netem()

    def _finish(self):
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
        self._is_prepared = False

    def _generate_stimuli(self, type_id, table_id, ids_to_generate, overwrite: bool = False):
        for entry_id in ids_to_generate:
            if not overwrite and is_stimuli_available(type_id, table_id, entry_id, "0"):
                print(f" Stimuli {get_video_id(type_id, table_id, entry_id)} already available - skipped. ")
                continue

            retry_counter = 0
            is_successful_or_canceled = False
            while not is_successful_or_canceled:
                try:
                    self._prepare(type_id, table_id, entry_id)
                    wait_countdown(SHORT_WAITING)
                    excerpt_duration = convert_to_seconds(get_end(type_id, table_id, entry_id)) - \
                                       convert_to_seconds(get_start(type_id, table_id, entry_id))
                    # estimate timespan to be recorded - to be careful we double the duration and add four
                    # minutes (assumed maximum time for youtube to adapt playback to rate) and add some
                    # extra time during which e.g. the overflow can be shown
                    time_str = convert_to_timestr(excerpt_duration * 2.0 + 180 + 20)
                    # time_str = "00:01:00"
                    self._execute(time_str)
                    wait_countdown(SHORT_WAITING)
                    is_successful_or_canceled = True
                except RuntimeError as err:
                    traceback.print_exc()
                    print(f"RuntimeError while generating stimuli : {type_id}-{table_id}-{entry_id}")
                    print(f"Error : {err}")
                    if retry_counter < MAX_RETRIES:
                        print(f"Retrying in a few seconds ({MAX_RETRIES - retry_counter} attempt(s) left)")
                        wait_countdown(LONG_WAITING)
                        retry_counter = retry_counter + 1
                    else:
                        # uncomment the following lines to allow manual retries - TODO: should be a flag
                        # input_text = input(f"Maximum number of retries reached - try again? (y/N)")
                        # if not (input_text == "y" or input_text == "Y"):
                        if True:
                            raise
                finally:
                    self._finish()

    def _perform_postprocessing(self, type_id, table_id, ids_to_process, overwrite: bool = False):
        trigger_dir = config.trigger_image_path.get()
        for entry_id in ids_to_process:
            video_id_in = get_video_id(type_id, table_id, entry_id, "0")
            video_id_out = get_video_id(type_id, table_id, entry_id, "1")
            if not overwrite and is_stimuli_available(type_id, table_id, entry_id, "1"):
                print(f" Stimuli {get_video_id(type_id, table_id, entry_id)} postprocessed filed exists - skipped. ")
                continue

            postprocessor = PostProcessor()
            print(f"Processing: {video_id_in}")
            # print("Semi-manual post-processing starts... ")
            # print("Please use a video player of your choice to answer the following questions.")
            # print("")
            # t_init_buf = str(
            #    input(f"Time until playback starts (T_init + time to fill playback buffer) [hh:mm:ss.xxx]: "))
            # t_raw_start = str(input(f"Time when relevant section starts in raw stimuli video [hh:mm:ss.xxx]: "))
            # d_start_to_end = int(input(f"Duration from t_start to t_end in seconds [s]: "))

            # auto-detect video t_init_buf, t_raw_start, t_raw_end
            unprocessed_video_path = f"{os.path.join(config.video_capture_path.get(), video_id_in)}.avi"
            trigger_image_start = os.path.join(trigger_dir, f"{type_id}-{table_id}_start.png")
            trigger_image_end = os.path.join(trigger_dir, f"{type_id}-{table_id}_end.png")
            print("Detecting start of stimuli video section... ", end='')
            start_frame_nr = determine_frame(unprocessed_video_path, trigger_image_start)
            t_raw_start = frame_to_time(unprocessed_video_path, start_frame_nr)
            print(f"{t_raw_start} s")

            t_detect_start = max(0, t_raw_start - (2 * VIDEO_PRE_START))

            print(f"Detecting start of video playback (search starts at: {t_detect_start} s) ... ", end='')
            t_init_buf = determine_video_start(unprocessed_video_path, t_detect_start)
            if not t_init_buf:
                print(f"failed. (Is the input video \"{unprocessed_video_path}\" correct?)")
                continue
            print(f"{t_init_buf} s")

            if t_init_buf > t_raw_start:
                raise RuntimeError(
                    f"Detected end of buffer initialization (t_init_buf, start of video playback) at {t_init_buf}s "
                    f"is later than start of stimuli at {t_raw_start}s ! Check detection thresholds.")

            print("Detecting end of stimuli video section... ", end='')
            t_raw_end = frame_to_time(unprocessed_video_path,
                                      determine_frame(unprocessed_video_path, trigger_image_end, start_frame_nr))
            print(f"{t_raw_end} s")
            d_start_to_end = t_raw_end - t_raw_start

            if t_raw_start > t_raw_end:
                raise RuntimeError(
                    f"Detected start of stimuli section at {t_raw_start}s is later than the detected end "
                    f"at {t_raw_end}s ! Check trigger images and verify that they are part of the recorded stimuli.")

            print("Cutting and merging video stimuli...")
            postprocessor.process(video_id_in, video_id_out,
                                  convert_to_timestr(t_init_buf),
                                  convert_to_timestr(t_raw_start),
                                  convert_to_timestr(d_start_to_end))
            print(f"Finished post-processing: {video_id_in} ==> {video_id_out}")

        """
        Start coordinating the emulation run for generating one or more stimuli.

        Parameter
        ----------
        type_ids : List[str]
            Specifies parameter stimuli type id, e.g. "VS"
        table_ids : List[str]
            Specifies parameter stimuli table id, e.g. "A"
            
        Attributes
        ----------
        entry_ids : List[str]
            Specifies parameter stimuli table id, e.g. "A"
            If an empty list is specified, all entry-ids available will be selected.
        generate_stimuli : bool
            Specify if new stimuli should be generated/recorded
        postprocessing : bool
            Specify if postprocessing should be applied
        """

    def start(self, type_ids: List[str], table_ids: List[str], entry_ids: List[str] = [],
              generate_stimuli: bool = True, postprocessing: bool = True, overwrite: bool = False):

        load_parameter_file(config.parameter_file.get())

        type_id = type_ids[0]  # TODO: extend to process all elements
        table_id = table_ids[0]

        if len(entry_ids) == 0:
            ids_to_evaluate = get_entry_ids(type_id, table_id)
        else:
            ids_available = get_entry_ids(type_id, table_id)
            len_ei = len(entry_ids)
            ids_ok = any(entry_ids == ids_available[i:len_ei + i] for i in range(len(ids_available) - len_ei + 1))
            if not ids_ok:
                raise RuntimeError(
                    f"Not all stimuli ids {entry_ids} are available in \"{config.parameter_file.get()}\"")
            ids_to_evaluate = entry_ids

        # ids_to_evaluate =  ['1'] #,'5','4','3','2','1']

        if ids_to_evaluate == None:
            raise RuntimeError(f"No Stimuli-IDs to evaluate - check parameter file \"{config.parameter_file.get()}\"")

        try:
            if generate_stimuli:
                self._generate_stimuli(type_id, table_id, ids_to_evaluate, overwrite)

            if postprocessing:
                self._perform_postprocessing(type_id, table_id, ids_to_evaluate, overwrite)

        except RuntimeError as err:
            traceback.print_exc()
            print(
                "******************************************************************************************************")
            print(f"RuntimeError occured: {err}")
            print(f"Coordinated QoEmu run canceled.")
            print(
                "******************************************************************************************************")


if __name__ == '__main__':
    # executed directly as a script
    print("Coordinator main started")

    coordinator = Coordinator()
    coordinator.start(['VS'], ['A'], ['1'], generate_stimuli=True, postprocessing=True, overwrite=False)
    # coordinator.start(['VS'],['B'],['2'],generate_stimuli=True,postprocessing=True)

    print("Done.")
