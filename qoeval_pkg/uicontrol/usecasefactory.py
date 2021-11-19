# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
import logging as log

from qoeval_pkg.uicontrol.usecase import UseCaseType, UseCase
from qoeval_pkg.uicontrol.youtube import _Youtube
from qoeval_pkg.uicontrol.webbrowsing import _WebBrowsing
from qoeval_pkg.uicontrol.applaunch import _AppLaunch
from qoeval_pkg.uicontrol.uitracing import _UiTracing


__all__ = ['_Youtube', '_WebBrowsing', '_AppLaunch', '_UiTracing']


class UseCaseFactory:
    def __init__(self, device, serialno):
        self._device = device
        self._serialno = serialno

    def create_use_case(self, uc_type: UseCaseType, **kwargs) -> UseCase:
        """
        Factory method to create a new use-case

        :rtype: UseCase
        """
        target_class = uc_type.value
        log.debug(f"Creating use case of type {target_class}")
        return globals()[target_class](self._device, self._serialno, **kwargs)
