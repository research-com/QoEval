import com.dtmilano.android.viewclient

import logging as log
import time
from com.dtmilano.android.adb import adbclient
from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState

# Links
YOUTUBE_URL_PREPREPARE = "https://youtu.be/someinvalidurl"  # preprep url used for triggering the app
YOUTUBE_URL_PREPARE = "https://youtu.be/nLyC7U850Xs"  # Youtube video used in preparation process

# View IDs
_ID_PLAYER = "com.google.android.youtube:id/watch_player"
_ID_PAUSE = "com.google.android.youtube:id/player_control_play_pause_replay_button"
_ID_FULLSCREEN = "com.google.android.youtube:id/fullscreen_button"
_ID_NO_FULLSCREEN_INDICATOR = "com.google.android.youtube:id/channel_navigation_container"
_ID_AUTONAV = "com.google.android.youtube:id/autonav_toggle_button"
_ID_OVERFLOW = "com.google.android.youtube:id/player_overflow_button"
_ID_RESOLUTION = "com.google.android.youtube:id/list_item_text_secondary"

_SHOW_RESOLUTION_TIMESPAN = 15


def _touch_view_by_id(vc, id: str):
    # find and touch Youtube player window
    vc.dump(window=-1, sleep=0)
    player_view = vc.findViewById(id)
    if player_view:
        log.debug(f"View {id} found!")
        # log.debug(player_view.__tinyStr__())
        player_view.touch()
    else:
        log.error(f"View {id} NOT found!")


def _pause_player(vc):
    # pause a playing youtube video
    vc.dump(window=-1, sleep=0)
    player_view = vc.findViewById(_ID_PLAYER)
    if player_view:
        log.debug(f"View {_ID_PLAYER} found!")
        center = player_view.getCenter()
        player_view.touch()
        time.sleep(0.5)
        vc.touch(center[0], center[1])
    else:
        log.error(f"View {_ID_PLAYER} NOT found!")
    return player_view


def _touch_overflow_button(vc):
    vc.dump(window=-1, sleep=0)
    # overflow_view = vc.findViewById(_ID_OVERFLOW)
    # workaround: overflow is out of vision on emulator(?) - position is reported as 0,0
    #             therefore, we locate the AUTONAV button and touch with an appropriate offset
    autonav_view = vc.findViewById(_ID_AUTONAV)
    if autonav_view:
        log.debug(f"AUTONAV Position and Size: {autonav_view.getPositionAndSize()}")
        delta_x = autonav_view.getPositionAndSize()[3]
        log.debug(f"delta_x to touch overflow button based on AUTONAV position is {delta_x} pixels")
        autonav_view.touch(adbclient.DOWN_AND_UP, delta_x)
    else:
        log.error("overflow_view NOT found!")


class _Youtube(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self.url = kwargs.get("url")
        self.show_resolution = True
        self._vc = None

    def prepare(self):
        """
        Prepare the device for youtube playback
        """
        log.debug(f"prepare: Youtube use-case for device with serialno: {self.serialno}")
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')

        # reset youtube app
        self.device.shell("pm clear com.google.android.youtube")

        # device.shell(f"am broadcast -a {intent_name}")
        # start some arbitrary video so we can switch to fullscreen mode while playing
        self.device.shell(f"am start -a android.intent.action.VIEW \"{YOUTUBE_URL_PREPREPARE}\"")
        log.debug(f"Started intend with pre-prepare video url: \"{YOUTUBE_URL_PREPREPARE}\"")
        time.sleep(10)
        self.device.shell(f"am start -a android.intent.action.VIEW \"{YOUTUBE_URL_PREPARE}\"")
        log.debug(f"Started intend with prep video url: \"{YOUTUBE_URL_PREPARE}\"")
        self._vc = com.dtmilano.android.viewclient.ViewClient(
            *com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(serialno=self.serialno))
        # ViewClient.sleep(3)
        # vc.traverse()

        no_fullscreen_view = self._vc.findViewById(_ID_NO_FULLSCREEN_INDICATOR)
        if no_fullscreen_view:
            log.debug("currently not in fullscreen mode - switching to fullscreen")
            # _touch_player_window(self._vc)
            # _touch_pause_button(self._vc)
            _pause_player(self._vc)

            com.dtmilano.android.viewclient.ViewClient.sleep(3)

            _touch_view_by_id(self._vc, _ID_FULLSCREEN)

            log.debug("Waiting...")
            com.dtmilano.android.viewclient.ViewClient.sleep(3)

        _pause_player(self._vc)

        # set to medium volume (note: there seems to be no way to set a specific absolute value)
        set_audio = False
        if set_audio:
            log.info("Setting audio volume")
            for x in range(15):
                self.device.press('KEYCODE_VOLUME_DOWN')
            for x in range(9):
                self.device.press('KEYCODE_VOLUME_UP')

        log.info("Prepared to start target video...")
        com.dtmilano.android.viewclient.ViewClient.sleep(5)

        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self.url or len(self.url) == 0:
            log.warning("URL is not set")

        log.info(f"Starting target youtube video: {self.url}")

        self.device.shell(f"am start -a android.intent.action.VIEW \"{self.url}\"")

        if self.show_resolution:
            time.sleep(duration - _SHOW_RESOLUTION_TIMESPAN)
            log.debug("Showing overflow")
            # pausing youtube app
            _pause_player(self._vc)
            time.sleep(1)
            # self._vc.traverse()
            _touch_overflow_button(self._vc)
            time.sleep(_SHOW_RESOLUTION_TIMESPAN)
        else:
            time.sleep(duration)
        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        # stop youtube app (so we can keep the settings)
        self.device.shell("am force-stop com.google.android.youtube")
        # reset youtube app
        self.device.shell("pm clear com.google.android.youtube")
        self.state = UseCaseState.SHUTDOWN
