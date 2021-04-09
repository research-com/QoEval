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
    UI_TRACING = "_UiTracing"    # a special use-case for tracing user-interface elements


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
        if self.serialno == None:
            raise RuntimeError("no serial")
        self.time_end = None
        self.state = UseCaseState.CREATED

    def prepare(self):
        pass

    def execute(self,duration: float):
        self.time_end = time.time() + duration

    def shutdown(self):
        pass
