from qoemu_pkg.configuration import config

mobile_device_type_tooltip = ""
config.traffic_analysis_protocols.tooltip = ''
config.traffic_analysis_directions.tooltip = ''
config.resolution_override.tooltip = ''

config.net_device_name.tooltip = 'name of network interface connecting us to the Internet'
config.excluded_ports.tooltip = 'Ports not affected by netem'
config.traffic_analysis_bin_sizes.tooltip = 'Bin size thresholds [B] for creating packet histograms'
config.emulator_type.tooltip = 'Emulator Type'
config.show_device_screen_mirror.tooltip = 'for real device: Mirror the device screen while recording'
config.show_device_frame.tooltip = 'for Emulator: show device frame'
config.adb_device_serial.tooltip = 'ADB Device Serial Number - determine your device/emulator serial by using the ' \
                                   'command "adb devices" \n\n' \
                                   '1131FDD4003EW: serial number of a Pixel 5 real hardware device'
config.audio_device_real.tooltip = 'audio device to be used if a real hardware device is connected'
config.parameter_file.tooltip = 'Stimuli parameter file (CSV format)'
config.dynamic_parameter_path.tooltip = 'Path to dynamic parameter files'
config.trigger_image_path.tooltip = 'Path to trigger images for detecting start/end of relevant stimuli section'
config.video_capture_path.tooltip = 'Path where captured video files are stored (default: "~/stimuli")'
config.vd_path.tooltip = 'Path where Android virtual devices (avd) files are stored (default: "~/qoemu_avd")'
config.traffic_analysis_plot.tooltip = 'Enable traffic analysis'
config.traffic_analysis_live.tooltip = 'Enable live traffic analysis'
config.traffic_analysis_bpf_filter.tooltip = 'Berkley Packet Filter rule applied to analysis results'
config.net_em_sanity_check.tooltip = 'Perform additional check to detect invalid network emulation situations'
config.vid_start_detect_thr_size_normal_relevance.tooltip = 'size [B] of differential frame that triggers start of ' \
                                                            'video (normal relevance) '
config.vid_start_detect_thr_size_high_relevance.tooltip = 'size [B] of differential frame that triggers start of ' \
                                                          'video (high relevance, strong indicator) '
config.vid_start_detect_thr_nr_frames.tooltip = 'number of frames needed above the threshold to avoid false positives'
config.audio_target_volume.tooltip = 'post-processing: target audio volume (max. volume, in dB)'
