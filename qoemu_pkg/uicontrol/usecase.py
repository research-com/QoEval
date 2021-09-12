import time
from enum import Enum
import logging as log
# noinspection PyUnresolvedReferences
from com.dtmilano.android.adb.adbclient import Device


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

    def _touch_view_by_id(self, id: str, max_waiting_time: float = 0.5, text_input=None):
        end_time = time.time() + max_waiting_time
        while time.time() < end_time:
            # find view and touch element with specified id
            self._vc.dump(window=-1, sleep=0)
            target_view = self._vc.findViewById(id)
            if target_view:
                # log.debug(f"View {id} found!")
                # log.debug(target_view.__tinyStr__())
                target_view.touch()
                if text_input:
                    self.device.type(text_input)
                return

        log.error(f"View {id} NOT found!")
        raise RuntimeError(f"View {id} NOT found!")

    def _touch_view_by_text(self, text: str, max_waiting_time: float = 0.5, text_input=None):
        end_time = time.time() + max_waiting_time
        while time.time() < end_time:
            # find view and touch element with specified text
            self._vc.dump(window=-1, sleep=0)
            target_view = self._vc.findViewWithText(text)
            if target_view:
                # log.debug(f"View {id} found!")
                # log.debug(target_view.__tinyStr__())
                target_view.touch()
                if text_input:
                    self.device.type(text_input)
                return

        log.error(f"View with text {text} NOT found!")
        raise RuntimeError(f"View with text {text} NOT found!")

    def prepare(self):
        pass

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
