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



"""
import logging as log
import time

from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState, UseCaseInteractionElement, UseCaseInteraction

_SHORT_TIME = 2  # short waiting time [s]
_TIME_TO_SET_HOUR = "10"
_TIME_TO_SET_MINUTE = "00"


# TODO: refactor the handling of interactions - should be dynamic based on a config file
def _get_interactions(app_package: str):
    if app_package.startswith("de.sde.mobile"):  # Spiegel Online App
        allow_push = UseCaseInteractionElement(info="Allow push notifications", trigger_text="ERLAUBEN", max_wait=2)
        # wait = UseCaseInteractionElement(info="wait some time and go to home screen", key='KEYCODE_HOME', delay=8)
        return UseCaseInteraction(elements=[allow_push])
    return None


class _AppLaunch(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self._package = kwargs.get("package")
        self._activity = kwargs.get("activity")

    def prepare(self):
        """
        Prepare the device for launching the app
        """
        super().prepare()
        self.set_autotime(False)
        self.set_time(_TIME_TO_SET_HOUR, _TIME_TO_SET_MINUTE)
        installed_packages = self.device.shell("pm list packages")
        if installed_packages.find(self._package) == -1:
            log.error(f"Package {self._package} is not installed - please install via playstore or adb")
            return

        # reset app
        log.debug(f"Resetting app {self._package}")
        self.device.shell("am force-stop {self._package}")
        time.sleep(_SHORT_TIME)
        self.device.shell(f"pm clear {self._package}")
        time.sleep(_SHORT_TIME)

        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self._package or len(self._package) == 0 or not self._activity or len(self._activity) == 0:
            log.warning("package/activity is not set")
            start_parameter = self._package
        else:
            start_parameter = f"{self._package}/{self._activity}"

        log.info(f"Starting: {start_parameter}")

        self.device.shell(f"am start -n {start_parameter}")

        # time.sleep(_SHORT_TIME)
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()

        interactions = _get_interactions(self._package)
        if interactions:
            self._handle_interactions(interactions)

        time.sleep(duration)

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
