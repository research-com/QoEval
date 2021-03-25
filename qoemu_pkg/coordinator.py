#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""
from qoemu_pkg.capture.capture import Capture
from qoemu_pkg.configuration import emulator_type
from qoemu_pkg.emulator.emulator import EmulatorType, EmulatorOrientation
from qoemu_pkg.emulator.genymotion_emulator import GenymotionEmulator
from qoemu_pkg.emulator.standard_emulator import StandardEmulator
from qoemu_pkg.netem.netem import Connection
from qoemu_pkg.uicontrol.uicontrol import UiControl
from qoemu_pkg.uicontrol.usecase import UseCaseType

import logging as log
import threading
import time
import sys

DEVICE_NAME = "enp0s31f6"  # TODO: get from config file

def wait_countdown(time_in_sec: int):
    for i in range(time_in_sec):
        sys.stdout.write(f"\rWaiting: {time_in_sec-i} s")
        time.sleep(1)
        sys.stdout.flush()
    sys.stdout.write("\r                                              \n")

class Coordinator:
    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.capture = Capture()
        self.ui_control = UiControl()
        if emulator_type == EmulatorType.GENYMOTION:
            self.emulator = GenymotionEmulator()
        if emulator_type == EmulatorType.SDK_EMULATOR:
            self.emulator = StandardEmulator()
        self._is_prepared = False
        self.netem = None

    def prepare(self, stimuli_id: str):
        # self.emulator.delete_vd()
        self.emulator.launch(orientation=EmulatorOrientation.LANDSCAPE)
        # TODO: read parameters, instantiate and start network emulation
        self.netem = Connection("coord1", DEVICE_NAME,t_init=1000, rul=1000, rdl=1000, dul=25, ddl=20,
                                exclude_ports=[22,5000,5002])  # exclude ports used for nomachine/ssh remote control
                                # android_ip=self.emulator.get_ip_address())
        # set and execute a Youtube use case
        # Tagesschau Intro:
        # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/5lEd5D2J27Y?t=8")
        # Beethoven
        self.ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/TpWpqs864y0?t=3819")
        self.ui_control.prepare_use_case()
        self._is_prepared = True

    def execute(self):
        if not self._is_prepared:
            log.error("Cannot execute campaign - not prepared.")
            return

        # execute concurrently in separate threads
        ui_control_thread = threading.Thread(target=self.ui_control.execute_use_case, args=())
        capture_thread = threading.Thread(target=self.capture.start_recording, args=('output',))
        self.netem.enable_netem()
        ui_control_thread.start()
        capture_thread.start()
        capture_thread.join()
        ui_control_thread.join()
        self.netem.disable_netem()

    def finish(self):
        if self.netem:
            self.netem.cleanup()
            self.netem = None
        if not self._is_prepared:
            log.error("Cannot finish campaign - not prepared.")
            return
        self.ui_control.shutdown_use_case()
        self.emulator.shutdown()

if __name__ == '__main__':
    # executed directly as a script
    print("Coordinator main started")
    coordinator = Coordinator()
    coordinator.prepare('some id')
    wait_countdown(5)
    coordinator.execute()
    wait_countdown(20)
    coordinator.finish()

    print("Done.")