#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    UI control
"""
import logging as log
import time
import com.dtmilano.android.viewclient
from qoemu_pkg.uicontrol.usecase import UseCaseType, UseCaseState
from qoemu_pkg.uicontrol.usecasefactory import UseCaseFactory


class UiControl:
    def __init__(self, serialno: str):
        log.basicConfig(level=log.DEBUG)
        self._device = None
        self._serialno = serialno
        self._use_case_factory = None
        self._current_use_case = None
        self.is_connected = False

    def connect_device(self):
        self._device, self._serialno = \
            com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(serialno=self._serialno, verbose=True)

        if self._device.checkConnected():
            log.info(f"ADB connected to device with serial: {self._serialno}")
            self.is_connected = True
        else:
            log.error("ADB NOT connected")
            self.is_connected = False

        # log cpu utilization
        # log.info(device.shell("dumpsys cpuinfo"))

        # return to home screen
        self._device.press('KEYCODE_HOME', 'DOWN_AND_UP')

        self._use_case_factory = UseCaseFactory(self._device, self._serialno)

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

    def execute_use_case(self, duration: float):
        if not self._current_use_case:
            raise RuntimeError('Cannot execute use case - not prepared.')
        self._current_use_case.execute(duration)

    def shutdown_use_case(self):
        if not self._current_use_case:
            raise RuntimeError('Cannot shutdown use case - must be set first.')
        self._current_use_case.shutdown()
        self._current_use_case = None


if __name__ == '__main__':
    # executed directly as a script
    print("QoE User Interface control")
    # ui_control = UiControl("192.168.56.146:5555")
    ui_control = UiControl("11131FDD4003EW")

    # set and execute a Youtube use case
    # Tagesschau Intro:
    # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/5lEd5D2J27Y?t=8")
    # Tagesschau letzte Sendung Jan Hofer:
    # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://www.youtube.com/watch?v=1dxhytrMmkM?t=895")
    # Beethoven
    # ui_control.set_use_case(UseCaseType.YOUTUBE, url="https://youtu.be/TpWpqs864y0?t=3819")
    # ui_control.prepare_use_case()
    # ui_control.execute_use_case(30)
    # ui_control.shutdown_use_case()

    # set and execute a launch app use-case (see applaunch.py)
    # Spiegel Online App:
    # ui_control.set_use_case(UseCaseType.APP_LAUNCH, package="de.spiegel.android.app.spon",
    #                       activity=".activities.SplashScreenActivity")
    # Süddeutsche Zeitung App:
    # ui_control.set_use_case(UseCaseType.APP_LAUNCH, package="de.sde.mobile",
    #                         activity=".mainactivity.MainActivity")
    # ZDF App
    ui_control.set_use_case(UseCaseType.APP_LAUNCH, package="com.zdf.android.mediathek",
                                                    activity=".ui.common.MainActivity")

    ui_control.prepare_use_case()
    ui_control.execute_use_case(20)
    time.sleep(5)
    ui_control.shutdown_use_case()

    # open a webbpage
    # ui_control.set_use_case(UseCaseType.WEB_BROWSING, url="https://news.google.de")
    # ui_control.prepare_use_case()
    # ui_control.execute_use_case(60)
    # time.sleep(20)
    # ui_control.shutdown_use_case()

    # ui_control.set_use_case(UseCaseType.UI_TRACING,
    #                         elements=["com.google.android.youtube:id/watch_player",
    #                                  "com.google.android.youtube:id/player_control_play_pause_replay_button",
    #                                  "com.google.android.youtube:id/player_overflow_button",
    #                                  "com.google.android.youtube:id/list_item_text_secondary"])
    # ui_control.prepare_use_case()
    # ui_control.execute_use_case(600)
    # ui_control.shutdown_use_case()
