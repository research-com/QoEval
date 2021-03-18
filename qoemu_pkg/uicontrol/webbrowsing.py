"""
Use case which opens a webpage in the default browser

Requires URL to open

"""
import logging as log

from com.dtmilano.android.viewclient import ViewClient
from qoemu_pkg.uicontrol.usecase import UseCase, UseCaseState


class _WebBrowsing(UseCase):
    def __init__(self, device, **kwargs):
        super().__init__(device)
        self._url = kwargs.get("url")

    def prepare(self):
        """
        Prepare the device for opening the webpage (nothing to do)
        """
        if self.state != UseCaseState.CREATED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.CREATED')

        self.state = UseCaseState.PREPARED

    def execute(self, duration: int):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self._url or len(self._url) == 0:
            log.warning("url for web-browsing is not set")

        log.info(f"Opening webpage: {self._url}")

        package = 'com.android.chrome'
        activity = 'com.google.android.apps.chrome.Main'

        component = package + "/" + activity

        self.device.startActivity(component=component, uri=self._url)
        ViewClient.sleep(2)

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        # return to home screen
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')
        self.state = UseCaseState.SHUTDOWN
