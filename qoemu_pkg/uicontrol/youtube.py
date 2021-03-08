import com.dtmilano.android.viewclient

import logging as log
from usecase import UseCase, UseCaseState

# Links
YOUTUBE_URL_PREPARE = "https://youtu.be/nLyC7U850Xs"  # Youtube video used in preparation process

# View IDs

_ID_PLAYER = "com.google.android.youtube:id/watch_player"
_ID_PAUSE = "com.google.android.youtube:id/player_control_play_pause_replay_button"
_ID_FULLSCREEN = "com.google.android.youtube:id/fullscreen_button"


def _touch_player_window(vc):
    # find and touch Youtube player window
    vc.dump(window=-1, sleep=0)
    player_view = vc.findViewById(_ID_PLAYER)
    if player_view:
        log.debug(f"View {_ID_PLAYER} found!")
        log.debug(player_view.__tinyStr__())
        player_view.touch()
    else:
        log.error(f"View {_ID_PLAYER} NOT found!")
    return player_view


def _touch_pause_button(vc):
    # press pause button
    vc.dump(window=-1, sleep=0)
    play_pause_view = vc.findViewById(_ID_PAUSE)
    if play_pause_view:
        log.debug(f"play_pause_view {_ID_PAUSE} found!")
        log.debug(play_pause_view.__tinyStr__())
        play_pause_view.touch()
    else:
        log.error(f"play_pause_view {_ID_PAUSE} NOT found!")


def _touch_fullscreen_button(vc):
    full_screen_view = vc.findViewById(_ID_FULLSCREEN)
    if full_screen_view:
        log.debug("fullscreen_button found!")
        log.debug(full_screen_view.__tinyStr__())
        _touch_player_window(vc)  # TODO: check if correct
        full_screen_view.touch()
    else:
        log.error("fullscreen_button NOT found!")


class _Youtube(UseCase):
    def __init__(self, device, **kwargs):
        super().__init__(device)
        self.url = kwargs.get("url")

    def prepare(self):
        """
        Prepare the device for youtube playback
        """
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')

        # reset youtube app
        self.device.shell("pm clear com.google.android.youtube")

        # device.shell(f"am broadcast -a {intent_name}")
        # start some arbitrary video so we can switch to fullscreen mode while playing
        self.device.shell(f"am start -a android.intent.action.VIEW \"{YOUTUBE_URL_PREPARE}\"")

        vc = com.dtmilano.android.viewclient.ViewClient(
            *com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit())
        # ViewClient.sleep(3)
        # vc.traverse()

        _touch_player_window(vc)
        _touch_pause_button(vc)

        com.dtmilano.android.viewclient.ViewClient.sleep(3)

        _touch_fullscreen_button(vc)

        log.debug("Waiting...")
        com.dtmilano.android.viewclient.ViewClient.sleep(3)

        # pausing youtube app
        _touch_player_window(vc)
        _touch_pause_button(vc)

        log.info("Prepared to start target video...")
        com.dtmilano.android.viewclient.ViewClient.sleep(5)

        self.state = UseCaseState.PREPARED

    def execute(self):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self.url or len(self.url) == 0:
            log.warning("URL is not set")

        log.info(f"Starting target youtube video: {self.url}")

        self.device.shell(f"am start -a android.intent.action.VIEW \"{self.url}\"")

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        # stop youtube app (so we can keep the settings)
        self.device.shell("am force-stop com.google.android.youtube")
        # reset youtube app
        self.device.shell("pm clear com.google.android.youtube")
        self.state = UseCaseState.SHUTDOWN
