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
from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState


class _AppLaunch(UseCase):
    def __init__(self, device, **kwargs):
        super().__init__(device)
        self._package = kwargs.get("package")
        self._activity = kwargs.get("activity")

    def prepare(self):
        """
        Prepare the device for launching the app
        """
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')

        installed_packages = self.device.shell("pm list packages")
        if installed_packages.find(self._package) == -1:
            log.error(f"Package {self._package} is not installed - please install via playstore or adb")
        else:
            self.state = UseCaseState.PREPARED

    def execute(self, duration: int):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self._package or len(self._package) == 0 or not self._activity or len(self._activity) == 0:
            log.warning("package/activity is not set")

        log.info(f"Starting: {self._package}/{self._activity}")

        self.device.shell(f"am start -n {self._package}/{self._activity}")

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        # stop app
        self.device.shell("am force-stop {self._package}")
        # reset app
        # self.device.shell("pm clear {self._package}")
        # return to home screen
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')
        self.state = UseCaseState.SHUTDOWN
