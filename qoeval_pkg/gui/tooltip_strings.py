# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Jan Andreas Krahl <krahl.jan@hm.edu>
#
# License:  LGPL 3.0 - see LICENSE file for details
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from qoeval_pkg.configuration import QoEvalConfiguration


def add_tooltips(qoeval_config: QoEvalConfiguration):
    """Adds tooltips to the config options"""
    qoeval_config.resolution_override.tooltip = ''
    qoeval_config.traffic_analysis_plot_settings.tooltip = 'Choose plot configurations. For each configuration a plot will be generated'

    qoeval_config.coordinator_generate_stimuli.tooltip = 'Check to genereate new stimuli videos'
    qoeval_config.coordinator_postprocessing.tooltip = 'Check to postprocess stimuli videos'
    qoeval_config.coordinator_overwrite.tooltip = 'Check to overwrite existing files'

    qoeval_config.net_device_name.tooltip = 'name of network interface connecting us to the Internet'
    qoeval_config.excluded_ports.tooltip = 'Ports not affected by netem'
    qoeval_config.traffic_analysis_bin_sizes.tooltip = 'Bin size thresholds [B] for packet size histogram data'
    qoeval_config.emulator_type.tooltip = 'Emulator Type'
    qoeval_config.show_device_screen_mirror.tooltip = 'for real device: Mirror the device screen while recording'
    qoeval_config.show_device_frame.tooltip = 'for Emulator: show device frame'
    qoeval_config.adb_device_serial.tooltip = 'ADB Device Serial Number - determine your device/emulator serial by using the ' \
                                       'command "adb devices" \n\n' \
                                       '1131FDD4003EW: serial number of a Pixel 5 real hardware device'
    qoeval_config.audio_device_real.tooltip = 'audio device to be used if a real hardware device is connected'
    qoeval_config.parameter_file.tooltip = 'Stimuli parameter file (CSV format)'
    qoeval_config.dynamic_parameter_path.tooltip = 'Path to dynamic parameter files'
    qoeval_config.trigger_image_path.tooltip = 'Path to trigger images for detecting start/end of relevant stimuli section'
    qoeval_config.video_capture_path.tooltip = 'Path where captured video files are stored (default: "~/stimuli")'
    qoeval_config.vd_path.tooltip = 'Path where Android virtual devices (avd) files are stored (default: "~/qoeval_avd")'
    qoeval_config.traffic_analysis_plot.tooltip = 'Enable data collection and plot creation for traffic analysis'
    qoeval_config.traffic_analysis_live.tooltip = 'Enable live traffic analysis'
    qoeval_config.net_em_sanity_check.tooltip = 'Perform additional check to detect invalid network emulation situations'
    qoeval_config.vid_start_detect_thr_size_normal_relevance.tooltip = 'size [B] of differential frame that triggers start of ' \
                                                                'video (normal relevance) '
    qoeval_config.vid_start_detect_thr_size_high_relevance.tooltip = 'size [B] of differential frame that triggers start of ' \
                                                              'video (high relevance, strong indicator) '
    qoeval_config.vid_start_detect_thr_nr_frames.tooltip = 'number of frames needed above the threshold to avoid false positives'
    qoeval_config.audio_target_volume.tooltip = 'post-processing: target audio volume (max. volume, in dB)'
    qoeval_config.resolution_override.tooltip = 'force Youtube to use a certain resolution or use parameter file settings (off)'
    qoeval_config.audio_erase_start_stop.tooltip = 'specifiy time frames for which audio will be erased'
