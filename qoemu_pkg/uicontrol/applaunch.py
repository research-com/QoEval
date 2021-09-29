"""
Use case which launches an app

Requires package name and activity name

1) To get the package name, e.g. for the spiegel app,
   you can use
   adb shell pm list packages | grep spiegel

2) To get the activity name, use the package name with monkey, e.g.
   adb shell monkey -p 'de.spiegel.android.app.spon' -v 1
   which will list the activity name, e.g.:
   ...;component=de.spiegel.android.app.spon/.activities.SplashScreenActivity;end


Note regarding the development of new user interactions: The following code fragment is
very helpful, if you need to find out the different IDs of user-interface elements to be clicked

        # while True:
        #     time.sleep(5)
        #     self._vc.dump(window=-1, sleep=0)
        #     self._vc.traverse()

"""
import logging as log
import time

from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState, UseCaseInteractionElement, UseCaseInteraction


# Specification of app names for specific app packages (TODO: automatically find out name)
_APP_NAMES = {'org.wikipedia': 'Wikipedia',
              'com.zdf.android.mediathek' : 'ZDFmediathek'}

_SHORT_TIME = 2  # short waiting time [s]
_RECORDING_START_OFFSET_TIME = 1 # assumed time for guaranteeing that recording has started [s]
_TIME_TO_SET_HOUR = "10"
_TIME_TO_SET_MINUTE = "00"
_RESET_ALL_APP_DATA = False   # if set to True, all cache and user data will be reset - not only the app cache


# TODO: refactor the handling of interactions - should be dynamic based on a config file
def _get_interactions(app_package: str):
    if app_package.startswith("de.sde.mobile"):  # Spiegel Online App
        allow_push = UseCaseInteractionElement(info="Allow push notifications", trigger_text="ERLAUBEN", max_wait=2)
        # wait = UseCaseInteractionElement(info="wait some time and go to home screen", key='KEYCODE_HOME', delay=8)
        return UseCaseInteraction(elements=[allow_push])
    if app_package.startswith("org.wikipedia"): # Wikipedia App
        search_input = UseCaseInteractionElement(info="Search input", trigger_text="Wikipedia durchsuchen",
                                                 user_input="Elbphilhar", max_wait=10)
        search_selection = UseCaseInteractionElement(info="Wikipedia search item selection",
                                                     trigger_text="Elbphilharmonie", max_wait=10)
        go_back_A = UseCaseInteractionElement(info="wait and press back", delay=60, key='KEYCODE_BACK')
        go_back_B = UseCaseInteractionElement(info="return to main screen", delay=1, key='KEYCODE_BACK')
        return UseCaseInteraction(elements=[search_input, search_selection, go_back_A, go_back_B, go_back_B])
    return None


class _AppLaunch(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self._package = kwargs.get("package")
        self._activity = kwargs.get("activity")

    def _reset_app_cache(self):
        if not self._package in _APP_NAMES:
            raise RuntimeError(f'Cannot reset only cached data for {self._package} - not in _APP_NAMES')
        self.device.shell("am force-stop com.android.settings")
        time.sleep(_SHORT_TIME)
        self.device.shell("am start -a android.settings.APPLICATION_SETTINGS")
        self._touch_view_by_id("com.android.settings:id/search_app_list_menu", text_input=_APP_NAMES[self._package])
        self._touch_view_by_id("android:id/title")
        self._touch_view_by_text("Speicher und Cache")
        self._touch_view_by_id("com.android.settings:id/button2")
        time.sleep(_SHORT_TIME)
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')

    def prepare(self):
        """
        Prepare the device for launching the app
        """
        super().prepare()
        # stop app (might be already active)
        self.device.shell(f"am force-stop {self._package}")
        self.set_autotime(False)
        self.set_time(_TIME_TO_SET_HOUR, _TIME_TO_SET_MINUTE)
        installed_packages = self.device.shell("pm list packages")
        if installed_packages.find(self._package) == -1:
            log.error(f"Package {self._package} is not installed - please install via playstore or adb")
            return
        time.sleep(_SHORT_TIME)
        # reset app
        if _RESET_ALL_APP_DATA:
            log.debug(f"Resetting app (cache and user data) for {self._package}")
            self.device.shell(f"pm clear {self._package}")
        else:
            log.debug(f"Resetting app (only user data) for {self._package}")
            self._reset_app_cache()
        time.sleep(_SHORT_TIME)

        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        time.sleep(_RECORDING_START_OFFSET_TIME)

        if not self._package or len(self._package) == 0 or not self._activity or len(self._activity) == 0:
            log.warning("package/activity is not set")
            start_parameter = self._package
        else:
            start_parameter = f"{self._package}/{self._activity}"

        log.info(f"Starting: {start_parameter}")
        start_time = time.time()
        self.device.shell(f"am start -n {start_parameter}")

        interactions = _get_interactions(self._package)
        if interactions:
            self._handle_interactions(interactions)

        # while True:
        #     time.sleep(5)
        #     self._vc.dump(window=-1, sleep=0)
        #     self._vc.traverse()

        if time.time() - start_time < duration:
            time.sleep(duration-(time.time()-start_time))

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        # stop app
        self.device.shell(f"am force-stop {self._package}")
        # reset app
        # self.device.shell(f"pm clear {self._package}")
        self.set_autotime(True)
        # return to home screen
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')
        self.state = UseCaseState.SHUTDOWN
