#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""

from qoemu_pkg.analysis import analysis
from qoemu_pkg.capture.capture import CaptureEmulator, CaptureRealDevice
from qoemu_pkg.postprocessing.bufferer.bufferer import Bufferer
from qoemu_pkg.postprocessing.buffering_generator import BufferingGenerator
from qoemu_pkg.postprocessing.postprocessor import PostProcessor
from qoemu_pkg.postprocessing.determine_video_start import determine_video_start
from qoemu_pkg.postprocessing.determine_image_timestamp import determine_frame, frame_to_time
from qoemu_pkg.configuration import MobileDeviceOrientation, QoEmuConfiguration
from qoemu_pkg.emulator.genymotion_emulator import GenymotionEmulator
from qoemu_pkg.emulator.standard_emulator import StandardEmulator
from qoemu_pkg.emulator.physical_device import PhysicalDevice
from qoemu_pkg.netem.netem import Connection, DynamicParametersSetup
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
DELAY_MEASUREMENT_BW_THRESH = 100  # threshold data rate for sanity delay measurement [kbit/s]
PROCESSING_BIAS = 3  # additional delay due to processing in emulator [ms]
VIDEO_PRE_START = 1.0  # start video VIDEO_PRE_START [s] early so that we can guarantee to see the trigger
# Note: Be careful with VIDEO_PRE_START - if set too high, we might miss rebuffering
VIDEO_T_INIT_TOLERANCE = 0.5  # when detecting end of T_INIT and comparing to start of stimuli, tolerate [s]
MAX_RETRIES = 2  # number of retries when generating a stimuli fails
SHORT_WAITING = 3  # short waiting time [s]
LONG_WAITING = 60  # long waiting time [s]


def gen_log_file(qoemu_config: QoEmuConfiguration):
    return os.path.join(qoemu_config.video_capture_path.get(), 'qoemu.log')


FINISH_CAMPAIGN_LOG = "Campaign finished for stimulus: "
FINISH_POST_LOG = "Finished post-processing: "
_AUTO_CODEC = "auto"


class Coordinator:
    """
            Coordinate the emulation run for generating one or more stimuli.
    """

    def __init__(self, qoemu_config: QoEmuConfiguration):
        log.basicConfig(level=log.DEBUG)
        self.qoemu_config = qoemu_config
        self.ui_control = UiControl(self.qoemu_config.adb_device_serial.get())
        if self.qoemu_config.emulator_type.get() == MobileDeviceType.GENYMOTION:
            self.emulator = GenymotionEmulator(self.qoemu_config)
            self.capture = CaptureEmulator(self.qoemu_config)
        if self.qoemu_config.emulator_type.get() == MobileDeviceType.SDK_EMULATOR:
            self.emulator = StandardEmulator(self.qoemu_config)
            self.capture = CaptureEmulator(self.qoemu_config)
        if self.qoemu_config.emulator_type.get() == MobileDeviceType.REAL_DEVICE:
            self.emulator = PhysicalDevice(self.qoemu_config, self.qoemu_config.show_device_screen_mirror.get())
            self.capture = CaptureRealDevice(self.qoemu_config)

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
            if len(filter_rule) > 0:
                filter_rule = f"{filter_rule} && "
            filter_rule = f"{filter_rule} !(tcp port {p}) && !(udp port {p})"
        log.debug(f"_get_bpf_rule filter rule: {filter_rule}")
        return filter_rule

    def _get_uc_type(self) -> UseCaseType:
        if self._type_id.startswith("VS"):
            return UseCaseType.YOUTUBE
        elif self._type_id.startswith("WB"):
            return UseCaseType.WEB_BROWSING
        elif self._type_id.startswith("AL"):
            return UseCaseType.APP_LAUNCH
        raise RuntimeError(f'Use-case type of \"{self._type_id}\" is unknown.')

    def _get_uc_orientation(self) -> MobileDeviceOrientation:
        if self._get_uc_type() == UseCaseType.YOUTUBE:
            return MobileDeviceOrientation.LANDSCAPE
        else:
            return MobileDeviceOrientation.PORTRAIT

    def _prepare(self, type_id: str, table_id: str, entry_id: str):
        if self._is_prepared:
            raise RuntimeError(
                f"Coordinator is already prepared - cannot prepare again before finish has been called.")

        self._gen_log = open(gen_log_file(self.qoemu_config), "a+")

        self._type_id = type_id
        self._table_id = table_id
        self._entry_id = entry_id
        self._params = get_parameters(self._type_id, self._table_id, self._entry_id)
        log.debug(f"Preparing {type_id}-{table_id}-{entry_id} with parameters: {self._params}")
        self.output_filename = get_video_id(self.qoemu_config, self._type_id, self._table_id, self._entry_id)
        time_string = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
        self._gen_log.write(f"{time_string} {self.output_filename} {self._params} ")
        # self.emulator.delete_vd()  # delete/reset virtual device - should be avoided
        # if use-case requires play services
        self.emulator.launch(orientation=self._get_uc_orientation())
        try:
            delay_bias_ul_dl = \
                (self.emulator.measure_rtt() + PROCESSING_BIAS) / 2  # can only measure RTT, assume 50%/50% ul vs. dl
        except RuntimeError as rte:
            self._gen_log.write(f" measuring delay bias failed - canceled. ")
            log.error(" measuring delay bias failed - check if you have Internet connectivity!")
            raise rte
        if delay_bias_ul_dl > self._params['dul'] or delay_bias_ul_dl > self._params['ddl']:
            self._gen_log.write(f" delay bias of {delay_bias_ul_dl}ms too high - canceled. ")
            raise RuntimeError(
                f"Delay bias of {delay_bias_ul_dl}ms exceeds delay parameter of {self._params['ddl']}ms! "
                f"Cannot emulate.")

        if self._params['dynamic'] and len(self._params['dynamic']) > 0:
            dynamic_parameter_variant = self._params['dynamic']
            dynamic_parameter_file = os.path.join(self.qoemu_config.dynamic_parameter_path.get(),
                                                  f"{dynamic_parameter_variant}_{int(self._params['rdl'])}.csv")
            log.debug(f"Dynamic connection parameters are active, using parameter file:{dynamic_parameter_file}")
            adaptive_params = DynamicParametersSetup.from_csv(dynamic_parameter_file, verbose=False)

            self.netem = Connection("coord1", self.qoemu_config.net_device_name.get(), t_init=self._params['t_init'],
                                    rul=self._params['rul'], rdl=self._params['rdl'],
                                    dul=(self._params['dul'] - delay_bias_ul_dl),
                                    ddl=(self._params['ddl'] - delay_bias_ul_dl),
                                    android_ip=self.emulator.get_ip_address(),
                                    # note: only valid, if not in host-ap mode
                                    exclude_ports=self.qoemu_config.excluded_ports.get(),
                                    # exclude ports, e.g. as used for ssh control
                                    dynamic_parameters_setup=adaptive_params)  # set of dynamic connection parameters
        else:
            # connection parameters are static, no dynamic_parameters_setup required
            self.netem = Connection("coord1", self.qoemu_config.net_device_name.get(), t_init=self._params['t_init'],
                                    rul=self._params['rul'], rdl=self._params['rdl'],
                                    dul=(self._params['dul'] - delay_bias_ul_dl),
                                    ddl=(self._params['ddl'] - delay_bias_ul_dl),
                                    android_ip=self.emulator.get_ip_address(),
                                    # note: only valid, if not in host-ap mode
                                    exclude_ports=self.qoemu_config.excluded_ports.get())  # exclude ports, e.g. as used for ssh

        url = f"{get_link(self._type_id, self._table_id, self._entry_id)}"
        if len(url) < 7:
            raise RuntimeError(f"Invalid Url: {url}")

        # create and prepare use-case
        if self._get_uc_type() == UseCaseType.YOUTUBE:
            start_time = convert_to_seconds(get_start(self._type_id, self._table_id, self._entry_id))
            start_time = start_time - VIDEO_PRE_START
            self.ui_control.set_use_case(UseCaseType.YOUTUBE, url=url, t=start_time,
                                         resolution=get_codec(self._type_id, self._table_id, self._entry_id))
            duration = convert_to_seconds(get_end(self._type_id, self._table_id, self._entry_id)) - start_time
        elif self._get_uc_type() == UseCaseType.WEB_BROWSING:
            self.ui_control.set_use_case(UseCaseType.WEB_BROWSING, url=url)
            duration = 60.0  # maximum length of web-browsing use-case
        elif self._get_uc_type() == UseCaseType.APP_LAUNCH:
            self.ui_control.set_use_case(UseCaseType.APP_LAUNCH, package=url.partition("/")[0],
                                         activity=url.partition("/")[2])
            duration = 30.0  # maximum length of app-launch use-case
        else:
            raise RuntimeError("Not a valid use case")

        self._gen_log.write(f"delay bias: {delay_bias_ul_dl}ms; url: {url}; len: {duration}s ")
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
        cfg_log = os.path.join(self.qoemu_config.video_capture_path.get(), f"{self.output_filename}.cfg")
        self.qoemu_config.store_netem_params(self._params)
        self.qoemu_config.save_to_file(cfg_log)

        # initialize traffic analysis - if enabled
        if self.qoemu_config.traffic_analysis_live.get() or self.qoemu_config.traffic_analysis_plot.get():
            self.stats_filepath = os.path.join(self.qoemu_config.video_capture_path.get(),
                                               f"{self.output_filename}_stats")
            self.analysis = analysis.DataCollector(virtual_interface_out=self.netem.virtual_device_out,
                                                   virtual_interface_in=self.netem.virtual_device_in,
                                                   duration=uc_duration, interval=100, filename=self.stats_filepath,
                                                   bpf_filter=self._get_bpf_rule())
            self.analysis.start_threads()

        # optional sanity check (can be disbled in configuration file)
        if self.qoemu_config.net_em_sanity_check.get():
            if self._params['rul'] < DELAY_MEASUREMENT_BW_THRESH or self._params['rdl']:
                log.warning("delay measurement in low-bandwidth situation - using higher relative tolerance")
                delay_tol_rel = DELAY_TOLERANCE_REL_LOWBW
            else:
                delay_tol_rel = DELAY_TOLERANCE_REL_NORMAL
            self.netem.enable_netem(consider_t_init=False)
            log.debug("network emulation sanity check - measuring delay while emulation is active...")
            measured_rtt_during_emulation = self.emulator.measure_rtt()
            max_allowed_rtt_during_emulation = (self._params['dul'] + self._params['ddl'] +
                                                max(DELAY_TOLERANCE_MIN,
                                                    delay_tol_rel * (self._params['dul'] + self._params['ddl'])))
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

        is_using_dynamic_params = self._params['dynamic'] and (len(self._params['dynamic']) > 0)

        self.netem.enable_netem(consider_t_init=True, consider_dynamic_parameters=is_using_dynamic_params)
        # input("netem active - check conditions on mobile device and press enter to continue...")

        if self.qoemu_config.traffic_analysis_live.get() or self.qoemu_config.traffic_analysis_plot.get():
            self.analysis.start()

        live_plot = None
        if self.qoemu_config.traffic_analysis_live.get():
            live_plot = analysis.LivePlot(self.analysis, analysis.PACKETS, analysis.ALL)

        ui_control_thread.start()
        capture_thread.start()

        if live_plot:
            log.debug("Showing live plot - close window to continue processing when use-case has finished.")
            live_plot.show()

        capture_thread.join()
        ui_control_thread.join()

        if self.qoemu_config.traffic_analysis_plot.get():
            self.analysis.wait_until_completed()
            for plot_setting in self.qoemu_config.traffic_analysis_plot_settings.get():
                plot = analysis.Plot(self.stats_filepath, 0, convert_to_seconds(capture_time), analysis.BYTES,
                                     plot_setting["directions"], plot_setting["protocols"], plot_setting["kind"])
                name = f'{self.stats_filepath}_{plot_setting["kind"]}'
                for direction in plot_setting["directions"]:
                    name = f'{name}_{direction}'
                for protocol in plot_setting["protocols"]:
                    name = f'{name}_{protocol}'
                plot.save_pdf(name)
                plot.save_png(name)

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
        self._export_parameter_table(type_id, table_id)
        for entry_id in ids_to_generate:
            if not overwrite and is_stimuli_available(self.qoemu_config, type_id, table_id, entry_id, "0"):
                print(f"Stimuli {get_video_id(self.qoemu_config, type_id, table_id, entry_id)} "
                      f"skipped (already available). ")
                continue

            alternative_stimuli = \
                get_stimuli_path(self.qoemu_config, type_id, table_id, entry_id, "0", True)

            if not overwrite and alternative_stimuli is not None:
                print(f"Stimuli {get_video_id(self.qoemu_config, type_id, table_id, entry_id)} "
                      f"skipped ({alternative_stimuli} was generated with the same relevant parameters "
                      f"and can be re-used). ")
                continue

            retry_counter = 0
            is_successful_or_canceled = False
            while not is_successful_or_canceled:
                try:
                    self._prepare(type_id, table_id, entry_id)
                    wait_countdown(SHORT_WAITING)
                    excerpt_duration = (convert_to_seconds(get_end(type_id, table_id, entry_id)) -
                                        convert_to_seconds(get_start(type_id, table_id, entry_id)))
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
                    log.info(f"{FINISH_CAMPAIGN_LOG}{get_video_id(self.qoemu_config, type_id, table_id, entry_id)}")

    def _perform_postprocessing(self, type_id, table_id, ids_to_process, overwrite: bool = False):
        self._export_parameter_table(type_id, table_id)
        trigger_dir = self.qoemu_config.trigger_image_path.get()
        self._type_id = type_id
        self._table_id = table_id
        for entry_id in ids_to_process:
            self._entry_id = entry_id
            video_id_in = get_video_id(self.qoemu_config, type_id, table_id, entry_id, "0")
            video_id_out = get_video_id(self.qoemu_config, type_id, table_id, entry_id, "1")
            if not overwrite and is_stimuli_available(self.qoemu_config, type_id, table_id, entry_id, "1"):
                print(f"Stimuli {get_video_id(self.qoemu_config, type_id, table_id, entry_id)} "
                      f"post-processed file exists - skipped. ")
                continue

            alternative_stimuli = \
                get_stimuli_path(self.qoemu_config, type_id, table_id, entry_id, "1", True)

            # we can re-use the existing post-processed file for VSB if an alternative stimuli exists
            # (since VSB use-cases might only differ in the buffer-generating parameters)
            if type_id == "VSB" and alternative_stimuli is not None:
                print(f"Stimuli {get_video_id(self.qoemu_config, type_id, table_id, entry_id)} "
                      f"post-processed file exists ({alternative_stimuli} was generated "
                      f"with the same relevant parameters and can be re-used). ")
                continue

            cfg_log = os.path.join(self.qoemu_config.video_capture_path.get(), f"{video_id_out}.cfg")

            if os.path.isfile(cfg_log):
                log.debug(f"Found an existing configuration - loading {cfg_log}")
                self.qoemu_config.read_from_file(cfg_log)
            else:
                # store a copy of the qoemu configuration used for post-processing (to be reproducible)
                self.qoemu_config.save_to_file(cfg_log)

            postprocessor = PostProcessor(self.qoemu_config)
            print(f"Processing: {video_id_in}")
            # print("Semi-manual post-processing starts... ")
            # print("Please use a video player of your choice to answer the following questions.")
            # print("")
            # t_init_buf = str(
            #    input(f"Time until playback starts (T_init + time to fill playback buffer) [hh:mm:ss.xxx]: "))
            # t_raw_start = str(input(f"Time when relevant section starts in raw stimuli video [hh:mm:ss.xxx]: "))
            # d_start_to_end = int(input(f"Duration from t_start to t_end in seconds [s]: "))

            # auto-detect video t_init_buf, t_raw_start, t_raw_end
            unprocessed_video_path = f"{os.path.join(self.qoemu_config.video_capture_path.get(), video_id_in)}.avi"

            if not os.path.isfile(unprocessed_video_path):
                # try to find alternative unprocessed input file
                alternative_stimuli = \
                    get_stimuli_path(self.qoemu_config, type_id, table_id, entry_id, "0", True)
                log.debug(f"Unprocessed video file {unprocessed_video_path} does not exist but found a valid "
                          f"alternative: {alternative_stimuli}")
                unprocessed_video_path = alternative_stimuli

            if not os.path.isfile(unprocessed_video_path):
                log.error(f"Cannot open unprocessed video file {unprocessed_video_path}")
                raise RuntimeError(f"Video file {unprocessed_video_path} does not exist.")

            trigger_image_start = os.path.join(trigger_dir, f"{type_id}-{table_id}_start.png")
            trigger_image_end = os.path.join(trigger_dir, f"{type_id}-{table_id}_end.png")
            if self._get_uc_type() == UseCaseType.APP_LAUNCH:
                # for the app launch use-case, the relevant section starts right at the capturing start time
                start_frame_nr = 0
                t_raw_start = 0
            else:
                print("Detecting start of stimuli video section... ", end='')
                start_frame_nr = determine_frame(unprocessed_video_path, trigger_image_start)
                t_raw_start = frame_to_time(unprocessed_video_path, start_frame_nr)
                print(f"{t_raw_start} s")

            t_init_buf_manual = self.qoemu_config.vid_init_buffer_time_manual.get()

            # only some of the use-case types require a detection of the initialization phase (t-init)
            if self._get_uc_type() == UseCaseType.YOUTUBE:
                is_normalizing_audio = True
                if t_init_buf_manual:
                    is_detecting_t_init = False
                else:
                    is_detecting_t_init = True
            else:
                is_detecting_t_init = False
                is_normalizing_audio = False

            # check: if a fixed-codec is used, auto-detection of t_init_buf does not work reliably
            if is_detecting_t_init and \
                    get_codec(self._type_id, self._table_id, self._entry_id) and \
                    get_codec(self._type_id, self._table_id, self._entry_id).lower() != _AUTO_CODEC and \
                    "" != get_codec(self._type_id, self._table_id, self._entry_id) and \
                    not t_init_buf_manual:
                log.warning(f"Stimuli uses a fixed codec but does not specify a manual "
                            f"buffer initialization time (VidInitBufferTimeManual)! This is NOT RECOMMENDED and "
                            f"might lead to invalid stimuli since auto-detection does not work reliably in "
                            f"this situation. Please specify VidInitBufferTimeManual in the configuration file"
                            f"of this stimuli.")

            if not t_init_buf_manual and is_detecting_t_init and not self._type_id == "VSB":
                t_detect_start = max(0, t_raw_start - (2.5 * VIDEO_PRE_START))
                print(f"Detecting start of video playback (search starts at: {t_detect_start} s) ... ", end='')
                t_init_buf = determine_video_start(self.qoemu_config, unprocessed_video_path, t_detect_start)
                if not t_init_buf:
                    print(f"failed. (Is the input video \"{unprocessed_video_path}\" correct?)")
                    continue
                print(f"{t_init_buf} s")
            else:
                if t_init_buf_manual:
                    print(f"Auto-detection disabled - manually specified start of buffering-phase "
                          f"(VidInitBufferTimeManual): {t_init_buf_manual} s")
                    t_init_buf = t_init_buf_manual
                else:
                    t_init_buf = 0.0

            if t_init_buf > t_raw_start:
                if t_init_buf - t_raw_start > VIDEO_T_INIT_TOLERANCE:
                    raise RuntimeError(
                        f"Detected end of buffer initialization (t_init_buf, start of video playback) at {t_init_buf}s "
                        f"is later than start of stimuli at {t_raw_start}s ! Check detection thresholds.")
                else:
                    log.warning(
                        "Detected end of t_init phase is later than detected stimuli start - but within tolerance.")
                    t_init_buf = t_raw_start

            print("Detecting end of stimuli video section... ", end='')
            t_raw_end = frame_to_time(unprocessed_video_path,
                                      determine_frame(unprocessed_video_path, trigger_image_end, start_frame_nr))
            print(f"{t_raw_end} s")
            d_start_to_end = t_raw_end - t_raw_start

            if self._get_uc_type() == UseCaseType.APP_LAUNCH:
                d_start_to_end = d_start_to_end + self.qoemu_config.app_launch_additional_recording_duration.get()
            elif self._get_uc_type() == UseCaseType.WEB_BROWSING:
                d_start_to_end = d_start_to_end + self.qoemu_config.web_browse_additional_recording_duration.get()

            if t_raw_start > t_raw_end:
                raise RuntimeError(
                    f"Detected start of stimuli section at {t_raw_start}s is later than the detected end "
                    f"at {t_raw_end}s ! Check trigger images and verify that they are part of the recorded stimuli.")

            if self._get_uc_type() == UseCaseType.APP_LAUNCH and \
                    self.qoemu_config.app_launch_vid_erase_box.get() is not None:
                # for the app launch use-case, we use a different default erase box
                erase_box = self.qoemu_config.app_launch_vid_erase_box.get()
            elif self._get_uc_type() == UseCaseType.WEB_BROWSING and \
                    self.qoemu_config.web_browse_vid_erase_box.get() is not None:
                erase_box = self.qoemu_config.app_launch_vid_erase_box.get()
            else:
                # use default value for all other use-case types
                erase_box = self.qoemu_config.vid_erase_box.get()

            print("Cutting and merging video stimuli...")
            postprocessor.process(video_id_in, video_id_out, t_init_buf, t_raw_start, d_start_to_end,
                                  normalize_audio=is_normalizing_audio,
                                  erase_audio=self.qoemu_config.audio_erase_start_stop.get(),
                                  erase_box = erase_box)
            print(f"{FINISH_POST_LOG}{video_id_in} ==> {video_id_out}")


    def _add_generated_buffering(self, type_id, table_id, ids_to_process, overwrite: bool = False):
        self._type_id = type_id
        self._table_id = table_id
        generator = BufferingGenerator(self.qoemu_config)
        for entry_id in ids_to_process:
            self._entry_id = entry_id
            if not overwrite and is_stimuli_available(self.qoemu_config, type_id, table_id, entry_id, "2"):
                print(f"Stimuli {get_video_id(self.qoemu_config, type_id, table_id, entry_id)} "
                      f"post-processed file (P2: generated_buffering) exists - skipped. ")
                continue
            generator.generate(type_id, table_id, entry_id)

    def _export_parameter_table(self, type_id, table_id):
        output_file = f"{type_id}-{table_id}"
        output_path = f"{os.path.join(self.qoemu_config.video_capture_path.get(), output_file)}.csv"
        export_entries(type_id, table_id, output_path, compact=False)
        output_path = f"{os.path.join(self.qoemu_config.video_capture_path.get(), output_file)}_compact.csv"
        export_entries(type_id, table_id, output_path, compact=True)

    def export_all_parameter_tables(self):
        load_parameter_file(self.qoemu_config.parameter_file.get())
        all_type_ids = get_type_ids()
        for type_id in all_type_ids:
            all_table_ids = get_table_ids(type_id)
            for table_id in all_table_ids:
                self._export_parameter_table(type_id, table_id)


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

    def start(self, type_ids: List[str], table_ids: List[str], entry_ids: List[str] = None,
              generate_stimuli: bool = True, postprocessing: bool = True, overwrite: bool = False):

        load_parameter_file(self.qoemu_config.parameter_file.get())

        type_id = type_ids[0]  # TODO: extend to process all elements
        table_id = table_ids[0]

        if entry_ids is None:
            ids_to_evaluate = get_entry_ids(type_id, table_id)
        else:
            ids_available = get_entry_ids(type_id, table_id)
            len_ei = len(entry_ids)
            ids_ok = any(entry_ids == ids_available[i:len_ei + i] for i in range(len(ids_available) - len_ei + 1))
            if not ids_ok:
                raise RuntimeError(
                    f"Not all stimuli ids {entry_ids} are available in \"{self.qoemu_config.parameter_file.get()}\"")
            ids_to_evaluate = entry_ids

        # ids_to_evaluate =  ['1'] #,'5','4','3','2','1']

        if ids_to_evaluate is None or len(ids_to_evaluate) < 1:
            raise RuntimeError(f"No Stimuli-IDs to evaluate for {type_id}-{table_id} - "
                               f"check parameter file \"{self.qoemu_config.parameter_file.get()}\"")

        try:
            if generate_stimuli:
                self._generate_stimuli(type_id, table_id, ids_to_evaluate, overwrite)

            if postprocessing:
                self._perform_postprocessing(type_id, table_id, ids_to_evaluate, overwrite)

            if type_id == "VSB":
                self._add_generated_buffering(type_id, table_id, ids_to_evaluate, overwrite)

        except RuntimeError as err:
            traceback.print_exc()
            print(
                "*****************************************************************************************************")
            print(f"RuntimeError occured: {err}")
            print(f"Coordinated QoEmu run canceled.")
            print(
                "*****************************************************************************************************")


def main():
    print("Coordinator main started")

    qoemu_config = QoEmuConfiguration()
    coordinator = Coordinator(qoemu_config)

    # export all (for documentation)
    # coordinator.export_all_parameter_tables()

    coordinator.start(['VSB'], ['B'], # ['1','2','3','4','5','6','7','8'],
                      generate_stimuli=False, postprocessing=True, overwrite=False)

    # coordinator.start(['VS'],['B'],['2'],generate_stimuli=True,postprocessing=False)

    print("Done.")


if __name__ == '__main__':
    # executed directly as a script
    main()
