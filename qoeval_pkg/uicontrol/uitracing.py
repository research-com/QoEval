# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
"""
Use case for tracing Android user interfaces

This use-case is not executed for stimuli-generation but instead is used during the development
process to allow a periodic tracing of ui elements.

"""
import time

import com.dtmilano.android.viewclient

import logging as log
from qoeval_pkg.uicontrol.usecase import UseCase, UseCaseState

_UPDATE_DELAY = 2  # update delay for refreshing the list of ui elements


def _touch_element(vc, element_id: str) -> bool:
    # find and touch Youtube player window
    vc.dump(window=-1, sleep=0)
    element_view = vc.findViewById(element_id)
    if element_view:
        log.debug(f"View {element_id} found!")
        log.debug(element_view.__tinyStr__())
        element_view.touch()
        return True
    else:
        log.debug(f"Looking for {element_id} - but NOT found!")
    return False


class _UiTracing(UseCase):
    def __init__(self, device, serialno, **kwargs):
        super().__init__(device, serialno)
        self._vc = None
        self.elements = kwargs.get("elements")
        if not self.elements:
            log.warning("List of ui-element strings is missing! Assuming empty list.")
            self.elements = []

    def prepare(self):
        """
        Prepare the device for ui tracing
        """
        self._vc = com.dtmilano.android.viewclient.ViewClient(
            *com.dtmilano.android.viewclient.ViewClient.connectToDeviceOrExit(serialno=self.serialno))
        self.state = UseCaseState.PREPARED

    def execute(self, duration: float):
        if self.state != UseCaseState.PREPARED:
            raise RuntimeError('Use case is in unexpected state. Should be in UseCaseState.PREPARED')

        log.info(f"Starting ui tracing on device with serial: {self.serialno}")

        self.time_end = time.time() + duration

        # ViewClient.sleep(_UPDATE_DELAY)
        self._vc.traverse()

        for id in self.elements:
            time.sleep(0.5)
            while not _touch_element(self._vc, id) and time.time() < self.time_end:
                time.sleep(_UPDATE_DELAY)
                self._vc.traverse()

        while time.time() < self.time_end:
            time.sleep(_UPDATE_DELAY)
            self._vc.dump(window=-1, sleep=0)
            self._vc.traverse()

        self.state = UseCaseState.EXECUTED

    def shutdown(self):
        log.debug("Shutdown of use-case...")
        self.state = UseCaseState.SHUTDOWN
