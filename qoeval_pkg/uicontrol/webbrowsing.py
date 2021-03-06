# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
"""
Use case which opens a webpage in the default browser

Requires URL to open

"""
import logging as log
import com.dtmilano.android.viewclient

from dataclasses import dataclass
from typing import List
from com.dtmilano.android.viewclient import ViewClient
from qoeval_pkg.uicontrol.usecase import UseCase, UseCaseState, UseCaseInteractionElement, UseCaseInteraction

_RESET_APP_PACKAGE = False

_TIME_TO_SET_HOUR = "14"
_TIME_TO_SET_MINUTE = "00"

_CHROME_PACKAGE = 'com.android.chrome'
_CHROME_ACTIVITY = 'com.google.android.apps.chrome.Main'
_CHROME_COMPONENT = _CHROME_PACKAGE + "/" + _CHROME_ACTIVITY
_PREPARATION_URL = "about:blank"
_ARBITRARY_CONTENT_URI = "https://www.hm.edu"  # a valid, arbitrary content URI
_CHROME_HISTORY_URL = "chrome://history"

# view IDs to controlling the use-case
_ID_TERMS_ACCEPT = "com.android.chrome:id/terms_accept"
_ID_NO_SYNC = "com.android.chrome:id/negative_button"
_ID_HOME = "com.android.chrome:id/home_button"

# view IDs to clear the browser history
_ID_CLEAR_BROWSING_DATA = "com.android.chrome:id/clear_browsing_data_button"
_ID_CONFIRM_CLEAR = "com.android.chrome:id/clear_button"
_ID_MENU = "com.android.chrome:id/menu_button"
_ID_HISTORY = "com.android.chrome:id/menu_item_text Verlauf"


# TODO: refactor the handling of interactions - should be dynamic based on a config file
def _get_interactions(url: str):
    if url.startswith("https://www.google.de"):
        enter_search = UseCaseInteractionElement(info="enter search term", trigger_id="com.android.chrome:id/url_bar",
                                             user_input="Perpignan", key='KEYCODE_ENTER', delay=1)
        # click_wiki = WebInteractionElement("click on wikipedia link", None, "https://de.wikipedia.org/wiki/Perpignan",
        #                                   None, None, 5)
        # wait = UseCaseInteractionElement(info="wait some time and go to home screen", key='KEYCODE_HOME', delay=60)
        return UseCaseInteraction(elements=[enter_search])
    return None


class _WebBrowsing(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self._url = kwargs.get("url")

    def _reset_app_package(self):
        # reset youtube app
        self.device.shell("pm clear com.android.chrome")

        # start chrome
        self.device.startActivity(component=_CHROME_COMPONENT, uri=_PREPARATION_URL)
        ViewClient.sleep(5)
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        # self.device.press('KEYCODE_ENTER')
        self._touch_view_by_id(_ID_TERMS_ACCEPT)  # accept chrome terms of usage
        ViewClient.sleep(5)
        self._touch_view_by_id(_ID_NO_SYNC)
        ViewClient.sleep(5)

    def _clear_browser_cache(self):
        # start chrome
        self.device.startActivity(component=_CHROME_COMPONENT, uri=_PREPARATION_URL)
        ViewClient.sleep(5)
        # while True:
        #     self._vc.dump(window=-1, sleep=0)
        #    self._vc.traverse()
        #    ViewClient.sleep(5)
        self._touch_view_by_id("com.android.chrome:id/tab_switcher_button")
        self._touch_view_by_id("com.android.chrome:id/menu_button")
        self._touch_view_by_text("Alle Tabs schlie??en", 5)
        self._touch_view_by_id("com.android.chrome:id/new_tab_view")
        ViewClient.sleep(2)
        self.device.startActivity(component=_CHROME_COMPONENT,
                                  uri=_ARBITRARY_CONTENT_URI)  # to add something to history
        ViewClient.sleep(3)
        # self._touch_view_by_id(_ID_MENU, 5)
        # ViewClient.sleep(3)
        # self._touch_view_by_id(_ID_HISTORY, 5)
        self._touch_view_by_id("com.android.chrome:id/location_bar", 5, _CHROME_HISTORY_URL)
        self.device.press('KEYCODE_ENTER')
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        self._touch_view_by_id(_ID_CLEAR_BROWSING_DATA, 5)
        self._touch_view_by_id(_ID_CONFIRM_CLEAR, 5)
        self._touch_view_by_id(_ID_HOME, 5)
        ViewClient.sleep(2)
        self.device.startActivity(component=_CHROME_COMPONENT, uri=_PREPARATION_URL)
        ViewClient.sleep(5)

    def prepare(self):
        """
        Prepare the device for opening the webpage (nothing to do)
        """

        super().prepare()
        self.set_autotime(False)
        self.set_time(_TIME_TO_SET_HOUR, _TIME_TO_SET_MINUTE)

        log.debug(f"Preparing web url: \"{_PREPARATION_URL}\"")

        if _RESET_APP_PACKAGE:
            self._reset_app_package()
        else:
            self._clear_browser_cache()

        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        if not self._url or len(self._url) == 0:
            log.warning("url for web-browsing is not set")

        log.info(f"Opening webpage: {self._url}")

        # Variant 1: directly open uri
        # self.device.startActivity(component=_CHROME_COMPONENT, uri=self._url)
        # Variant 2: type in location bar
        self._touch_view_by_id("com.android.chrome:id/location_bar", 5, self._url)
        self.device.press('KEYCODE_ENTER')
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        ViewClient.sleep(1)
        interactions = _get_interactions(self._url)
        if interactions:
            self._handle_interactions(interactions)
        else:
            log.debug(f"No interactions defined for {self._url} - waiting a few seconds and terminating.")
            ViewClient.sleep(10)
        # self._vc.dump(window=-1, sleep=0)
        # self._vc.traverse()
        # ViewClient.sleep(10)

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        self.set_autotime(True)
        # return to home screen
        self.device.press('KEYCODE_HOME', 'DOWN_AND_UP')
        self.state = UseCaseState.SHUTDOWN
