#!/usr/bin/env python3
"""
    Stimuli campaign coordinator
"""
from qoemu_pkg.capture.capture import Capture
from qoemu_pkg.configuration import emulator_type
from qoemu_pkg.emulator.emulator import EmulatorType, EmulatorOrientation
from qoemu_pkg.emulator.genymotion_emulator import GenymotionEmulator
from qoemu_pkg.emulator.standard_emulator import StandardEmulator
from qoemu_pkg.uicontrol.uicontrol import UiControl
from qoemu_pkg.uicontrol.usecase import UseCaseType

import logging as log
import threading
import time


class Coordinator:
    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self.capture = Capture()
        self.ui_control = UiControl()
        if emulator_type == EmulatorType.GENYMOTION:
            self.emulator = GenymotionEmulator()
        if emulator_type == EmulatorType.SDK_EMULATOR:
            self.emulator = StandardEmulator()
        self.netem = None  # TODO: read parameters, instantiate and start network emulation
        self._is_prepared = False

    def prepare(self, stimuli_id: str):
        self.emulator.launch_emulator(orientation=EmulatorOrientation.LANDSCAPE)
        # set and execute a Youtube use case
        # Tagesschau Intro:
        # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/5lEd5D2J27Y?t=8")
        # Beethoven
        self.ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/TpWpqs864y0?t=3819")
        self.ui_control.prepare_use_case()
        self._is_prepared = True
        pass

    def execute(self):
        if not self._is_prepared:
            log.error("Cannot execute campaign - not prepared.")
            return
        # execute concurrently in separate threads
        ui_control_thread = threading.Thread(target=self.ui_control.execute_use_case, args=())
        capture_thread = threading.Thread(target=self.capture.start_recording, args=('output',))
        ui_control_thread.start()
        capture_thread.start()
        capture_thread.join()
        ui_control_thread.join()


    def finish(self):
        if not self._is_prepared:
            log.error("Cannot finish campaign - not prepared.")
            return
        self.ui_control.shutdown_use_case()




if __name__ == '__main__':
    # executed directly as a script
    print("Coordinator main started")
    coordinator = Coordinator()
    coordinator.prepare('some id')
    coordinator.execute()
    coordinator.finish()

    print("Done.")