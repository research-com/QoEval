#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    UI control
"""
import time
import logging as log
import com.dtmilano.android.viewclient
from qoemu_pkg.uicontrol.usecase import UseCaseType, UseCaseState
from qoemu_pkg.uicontrol.usecasefactory import UseCaseFactory


class UiControl:
    def __init__(self):
        log.basicConfig(level=log.DEBUG)
        self._device = None
        self._use_case_factory = None
        self._current_use_case = None
        self.is_connected = False

    def connect_device(self):
        self._device, serialno = com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(verbose=True)

        if self._device.checkConnected():
            log.info(f"ADB connected to device with serial: {serialno}")
            self.is_connected = True
        else:
            log.error("ADB NOT connected")
            self.is_connected = False

        # log cpu utilization
        # log.info(device.shell("dumpsys cpuinfo"))

        # return to home screen
        self._device.press('KEYCODE_HOME', 'DOWN_AND_UP')

        self._use_case_factory = UseCaseFactory(self._device)

    def set_use_case(self, use_case_type: UseCaseType, **kwargs: object):
        if not self.is_connected:
            # try to connect
            self.connect_device()
            if not self.is_connected:
                log.error("Cannot set use-case, not connected.")
                return
        if self._current_use_case and self._current_use_case.state != UseCaseState.SHUTDOWN:
            log.error("There is already an active use-case! State: {_current_use_case.state.value}")
            return
        self._current_use_case = self._use_case_factory.create_use_case(use_case_type, **kwargs)

    def prepare_use_case(self):
        if not self._current_use_case:
            raise RuntimeError('Cannot prepare use case - must be set first.')
        self._current_use_case.prepare()

    def execute_use_case(self):
        if not self._current_use_case:
            raise RuntimeError('Cannot execute use case - not prepared.')
        self._current_use_case.execute()

    def shutdown_use_case(self):
        if not self._current_use_case:
            raise RuntimeError('Cannot shutdown use case - must be set first.')
        self._current_use_case.shutdown()
        self._current_use_case = None


if __name__ == '__main__':
    # executed directly as a script
    print("QoE User Interface control")
    ui_control = UiControl()

    # set and execute a Youtube use case
    # Tagesschau Intro:
    # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/5lEd5D2J27Y?t=8")
    # Beethoven
    ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/TpWpqs864y0?t=3819")
    ui_control.prepare_use_case()
    ui_control.execute_use_case()
    time.sleep(20)
    ui_control.shutdown_use_case()
