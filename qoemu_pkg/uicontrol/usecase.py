from enum import Enum
import logging as log
# noinspection PyUnresolvedReferences
from com.dtmilano.android.adb.adbclient import Device


# define available types of use-cases (used for factory)
class UseCaseType(Enum):
    YOUTUBE = "_Youtube"
    WEB_BROWSING = "_WebBrowsing"
    APP_LAUNCH = "_AppLaunch"


class UseCaseState(Enum):
    UNKNOWN = 0
    CREATED = 1
    PREPARED = 2
    EXECUTED = 3
    SHUTDOWN = 4


class UseCase:
    def __init__(self, device_to_use):
        # noinspection PyUnresolvedReferences
        log.basicConfig(level=log.DEBUG)
        self.device = device_to_use
        self.state = UseCaseState.CREATED

    def prepare(self):
        pass

    def execute(self):
        pass

    def shutdown(self):
        pass
