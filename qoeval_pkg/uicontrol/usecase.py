# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
import time
from enum import Enum
import logging as log
import com.dtmilano.android.viewclient
# noinspection PyUnresolvedReferences
from com.dtmilano.android.adb.adbclient import Device
from typing import List
from dataclasses import dataclass


# define available types of use-cases (used for factory)
class UseCaseType(Enum):
    YOUTUBE = "_Youtube"
    WEB_BROWSING = "_WebBrowsing"
    APP_LAUNCH = "_AppLaunch"
    UI_TRACING = "_UiTracing"  # a special use-case for tracing user-interface elements


class UseCaseState(Enum):
    UNKNOWN = 0
    CREATED = 1
    PREPARED = 2
    EXECUTED = 3
    SHUTDOWN = 4


@dataclass
class UseCaseInteractionElement:
    info: str                   # short information describing this interaction
    delay: float = 0.0          # delay (time) which needs to pass until interaction starts
    delay_id: str = None        # id which must disappear until the interaction starts
    trigger_id: str = None      # id which starts the interaction
    trigger_text: str = None    # text which needs to be on the screen when interaction starts
    user_input: str = None      # user input which is to be sent when the trigger has appeared
    key: str = None             # key to be pressed
    swipe: str = None           # swipe action to be done after trigger has started
    max_wait: float = 5.0       # maximum waiting time for waiting for ids
    touch: bool = True          # should the id be touched when it was found


@dataclass
class UseCaseInteraction:
    elements: List[UseCaseInteractionElement]


class UseCase:
    def __init__(self, device_to_use, serialno):
        # noinspection PyUnresolvedReferences
        log.basicConfig(level=log.DEBUG)
        self.device = device_to_use
        self.serialno = serialno
        if self.serialno is None:
            raise RuntimeError("no serial")
        self.time_end = None
        self._vc = None
        self.state = UseCaseState.CREATED

    def _touch_view_by_id(self, id: str, max_waiting_time: float = 0.5, text_input=None, do_touch=True):
        end_time = time.time() + max_waiting_time
        while time.time() < end_time:
            # find view and touch element with specified id
            self._vc.dump(window=-1, sleep=0)
            target_view = self._vc.findViewById(id)
            if target_view:
                # log.debug(f"View {id} found!")
                # log.debug(target_view.__tinyStr__())
                if do_touch:
                    target_view.touch()
                if text_input:
                    self.device.type(text_input)
                return

        log.error(f"View {id} NOT found!")
        raise RuntimeError(f"View {id} NOT found!")

    def _wait_until_id_not_found(self, id: str, max_waiting_time: float = 0.5):
        end_time = time.time() + max_waiting_time
        while time.time() < end_time:
            # find view and touch element with specified id
            self._vc.dump(window=-1, sleep=0)
            target_view = self._vc.findViewById(id)
            if not target_view:
                log.info(f"id {id} has disappeared")
                return
        log.warning(f"View {id} did not disappear!")

    def _touch_view_by_text(self, text: str, max_waiting_time: float = 0.5, text_input=None, do_touch=True):
        end_time = time.time() + max_waiting_time
        while time.time() < end_time:
            # find view and touch element with specified text
            self._vc.dump(window=-1, sleep=0)
            target_view = self._vc.findViewWithText(text)
            if target_view:
                # log.debug(f"View {id} found!")
                # log.debug(target_view.__tinyStr__())
                if do_touch:
                    target_view.touch()
                if text_input:
                    self.device.type(text_input)
                return

        log.error(f"View with text {text} NOT found!")
        raise RuntimeError(f"View with text {text} NOT found!")

    def _handle_interactions(self, interactions):
        for interaction in interactions.elements:
            log.debug(f"Handling interaction: {interaction.info}")
            if interaction.delay > 0:
                time.sleep(interaction.delay)
            # self._vc.dump(window=-1, sleep=0)
            # self._vc.traverse()
            if interaction.delay_id:
                self._wait_until_id_not_found(interaction.delay_id, interaction.max_wait)
            if interaction.trigger_id:
                self._touch_view_by_id(interaction.trigger_id, interaction.max_wait, interaction.user_input,
                                       do_touch=interaction.touch)
            if interaction.trigger_text:
                self._touch_view_by_text(interaction.trigger_text, interaction.max_wait, interaction.user_input,
                                         do_touch=interaction.touch)
            if interaction.key:
                self.device.press(interaction.key)
            if interaction.swipe:
                self.device.shell(f'input swipe {interaction.swipe}')

    def set_time(self, time_to_set_hour: str, time_to_set_minute: str):
        self.device.shell(f"am start -n com.android.settings/.Settings\$DateTimeSettingsActivity")
        self._touch_view_by_text("Uhrzeit", 5)
        self._touch_view_by_id("android:id/toggle_mode")
        self._touch_view_by_id("android:id/input_hour", 1.0, time_to_set_hour)
        self._touch_view_by_id("android:id/input_minute", 1.0, time_to_set_minute)
        self._touch_view_by_text("OK")
        time.sleep(1)
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')
        # while True:
        #     time.sleep(5)
        #     self._vc.dump(window=-1, sleep=0)
        #     self._vc.traverse()

    def set_autotime(self, state_auto: bool = True):
        if state_auto:
            s = "1"
        else:
            s = "0"
        self.device.shell(f"settings put global auto_time {s}")

    def prepare(self):
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')
        self._vc = com.dtmilano.android.viewclient.ViewClient(
            *com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(serialno=self.serialno))

    def execute(self, duration: float):
        self.time_end = time.time() + duration

    def shutdown(self):
        pass

    def set_media_volume(self, volume: int):
        # service call to set audio
        # 10: service call number
        # 3: audio stream type for media
        if volume < 0 or volume > 25:
            raise RuntimeError(f"Volume level must be in the range [0,25]! (You tried to set it to {volume}.)")
        self.device.shell(f"service call audio 10 i32 3 i32 {volume} i32 1")
