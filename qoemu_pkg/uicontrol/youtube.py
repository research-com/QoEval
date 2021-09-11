import com.dtmilano.android.viewclient

import logging as log
import time
import re
from com.dtmilano.android.adb import adbclient
from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState

# Links
YOUTUBE_URL_PREPREPARE = "https://youtu.be/someinvalidurl"  # preprep url used for triggering the app
YOUTUBE_URL_PREPARE_DEFAULT = "https://www.youtube.com/watch?v=GRVwYbQPFQQ"  # Youtube video used in preparation process

# Audio Settings
_MEDIA_VOLUME = 15

# View IDs
_ID_PLAYER = "com.google.android.youtube:id/watch_player"
_ID_PAUSE = "com.google.android.youtube:id/player_control_play_pause_replay_button"
_ID_FULLSCREEN = "com.google.android.youtube:id/fullscreen_button"
_ID_NO_FULLSCREEN_INDICATOR = "com.google.android.youtube:id/channel_navigation_container"
_ID_LIVE_CHAT_OVERLAY = "com.google.android.youtube:id/live_chat_overlay_button"
_ID_AUTONAV = "com.google.android.youtube:id/autonav_toggle_button"
_ID_OVERFLOW = "com.google.android.youtube:id/player_overflow_button"
_ID_RESOLUTION = "com.google.android.youtube:id/list_item_text_secondary"
_ID_SECONDARY = "com.google.android.youtube:id/list_item_text_secondary"

_SHOW_RESOLUTION_TIMESPAN = 15

# other assumptions
_ASSUMED_MAX_BUFFER_TIME = 10.0         # assumed maximum time for which youtube buffers video
_ASSUMED_POS_OUTSIDE_STIMULI = 0.0      # an arbitrary point in time within the video but outside the stimuli


def _get_intent_url(url, start_time):
    intent_url = f"{url}"
    if start_time is not None:
        # append ? or &t=[start time in seconds] to link (note: currently, youtube support only int values)
        if "?" in url:
            intent_url = f"{intent_url}&t={int(start_time)}"
        else:
            intent_url = f"{intent_url}?t={int(start_time)}"
    return intent_url

class _Youtube(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self.url = kwargs.get("url")
        self.start_time = kwargs.get("t")
        selected_resolution = kwargs.get("resolution")
        if selected_resolution is not None and selected_resolution.lower() != "auto":
            self.resolution = kwargs.get("resolution")
        else:
            self.resolution = None
        # Testing only: manually select resolution
        # self.resolution = "1080p"
        self.show_resolution = True

    def _pause_player(self):
        # pause a playing youtube video
        self._vc.dump(window=-1, sleep=0)
        player_view = self._vc.findViewById(_ID_PLAYER)
        if player_view:
            # log.debug(f"View {_ID_PLAYER} found!")
            center = player_view.getCenter()
            player_view.touch()
            time.sleep(0.5)
            self._vc.touch(center[0], center[1])
        else:
            log.error(f"View {_ID_PLAYER} NOT found!")
        return player_view

    def _touch_overflow_button(self):
        self._vc.dump(window=-1, sleep=0)
        # vc.traverse()
        overflow_view = self._vc.findViewById(_ID_OVERFLOW)
        if overflow_view and overflow_view.getPositionAndSize()[0] > 0 and overflow_view.getPositionAndSize()[1] > 0:
            # found a valid overflow element
            overflow_view.touch()
            return
        # workaround: if overflow is out of vision on emulator(?) - position is reported as 0,0
        # Thus, we need to detect a neighbouring button. Unfortunately, the youtube player ui
        # is somewhat dynamic at this point, so we need to check what situation we are in:
        # a) check if a chat-view button is there
        live_chat_view = self._vc.findViewById(_ID_LIVE_CHAT_OVERLAY)
        if live_chat_view:
            delta_x = live_chat_view.getPositionAndSize()[3]
            live_chat_view.touch(adbclient.DOWN_AND_UP, delta_x)
            return
        #  b) check for AUTONAV button and touch with an appropriate offset
        autonav_view = self._vc.findViewById(_ID_AUTONAV)
        if autonav_view:
            log.debug(f"AUTONAV Position and Size: {autonav_view.getPositionAndSize()}")
            delta_x = autonav_view.getPositionAndSize()[3]
            # log.debug(f"delta_x to touch overflow button based on AUTONAV position is {delta_x} pixels")
            autonav_view.touch(adbclient.DOWN_AND_UP, delta_x)
            return
        # c) until now, we did not find any known neighbouring button - our last chance: touch by hard-coded position
        log.warning("Could not determine position of overflow button dynamically, trying Pixel 5 position.")
        self._vc.touch(2280, 72)  # for google pixel 5 - other device might have the button at a different position

    def _is_paused(self):
        self._vc.dump(window=-1, sleep=0)
        return self._vc.findViewById(_ID_PAUSE) is not None

    def _unpause_player(self):
        if self._is_paused():
            self._touch_view_by_id(_ID_PAUSE)
        else:
            log.error("Cannot unpause - player is not paused.")

    def _set_resolution(self):
        log.debug(f"Manually selecting the resolution: {self.resolution}")
        self._pause_player()
        self._unpause_player()
        # time.sleep(1)
        self._touch_overflow_button()
        # time.sleep(1)
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        self._touch_view_by_id(_ID_SECONDARY)
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        # self._touch_view_by_text(self.resolution) -- cannot be used since we illegally might select Automatic
        end_time = time.time() + 3.0
        while (time.time() < end_time):
            # find view and touch element with specified text
            self._vc.dump(window=-1, sleep=0)
            target_views = self._vc.findViewsWithAttributeThatMatches(self._vc.textProperty,
                                                                      re.compile(f'{self.resolution}', re.IGNORECASE))
            if target_views is None:
                continue

            if len(target_views) > 1:
                log.error(f"Found multiple views matching {self.resolution}")
                continue

            if target_views[0]:
                target_views[0].touch()
                log.debug(f"Successfully selected resolution {self.resolution}")
                break

        if not target_views[0]:
            raise RuntimeError(f'Could not manually select resolution {self.resolution}')

        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        # un-pause player
        # self._unpause_player()
        # time.sleep(0.5)
        # self._pause_player()

    def prepare(self):
        """
        Prepare the device for youtube playback
        """
        log.debug(f"prepare: Youtube use-case for device with serialno: {self.serialno}")
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')

        # stop youtube app (since it might be running on the device and have cached data)
        self.device.shell("am force-stop com.google.android.youtube")
        time.sleep(2)

        # reset youtube app
        self.device.shell("pm clear com.google.android.youtube")

        # device.shell(f"am broadcast -a {intent_name}")
        # start some arbitrary video so we can switch to fullscreen mode while playing
        self.device.shell(f"am start -a android.intent.action.VIEW \"{YOUTUBE_URL_PREPREPARE}\"")
        log.debug(f"Started intend with pre-prepare video url: \"{YOUTUBE_URL_PREPREPARE}\"")
        time.sleep(10)
        if self.resolution:
            # in order to manually select the resolution, we must start with the true url (but no time-offset)
            prep_url = _get_intent_url(self.url, _ASSUMED_POS_OUTSIDE_STIMULI)
            if self.start_time is None or \
                    abs(_ASSUMED_POS_OUTSIDE_STIMULI - self.start_time) < _ASSUMED_MAX_BUFFER_TIME:
                raise RuntimeError(f'Use case wants to manually select the resolution but start_time {self.start_time} '
                                   f'is too close to preparation time position.')
        else:
            prep_url = YOUTUBE_URL_PREPARE_DEFAULT
        self.device.shell(f"am start -a android.intent.action.VIEW \"{prep_url}\"")
        log.debug(f"Started intend with prep video url: \"{prep_url}\"")
        self._vc = com.dtmilano.android.viewclient.ViewClient(
            *com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(serialno=self.serialno))
        # ViewClient.sleep(3)
        # vc.traverse()

        no_fullscreen_view = self._vc.findViewById(_ID_NO_FULLSCREEN_INDICATOR)
        if no_fullscreen_view:
            log.debug("currently not in fullscreen mode - switching to fullscreen")
            self._pause_player()

            com.dtmilano.android.viewclient.ViewClient.sleep(3)

            self._touch_view_by_id(_ID_FULLSCREEN)

            log.debug("Waiting...")
            com.dtmilano.android.viewclient.ViewClient.sleep(3)

        self._pause_player()

        # set media audio to medium volume
        self.set_media_volume(_MEDIA_VOLUME)

        # manually set the resolution (if specified)
        if self.resolution:
            self._set_resolution()

        log.info("Prepared to start target video...")
        com.dtmilano.android.viewclient.ViewClient.sleep(5)

        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self.url or len(self.url) == 0:
            log.warning("URL is not set")

        intent_url = _get_intent_url(self.url,self.start_time)

        log.info(f"Starting target youtube video: {intent_url}")

        self.device.shell(f"am start -a android.intent.action.VIEW \"{intent_url}\"")

        if self.show_resolution:
            time.sleep(duration - _SHOW_RESOLUTION_TIMESPAN)
            log.debug("Showing overflow")
            # pausing youtube app
            self._pause_player()
            time.sleep(1)
            # self._vc.traverse()
            self._touch_overflow_button()
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
