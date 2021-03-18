import logging as log

from qoemu_pkg.uicontrol.usecase import UseCaseType, UseCase
from qoemu_pkg.uicontrol.youtube import _Youtube
from qoemu_pkg.uicontrol.webbrowsing import _WebBrowsing
from qoemu_pkg.uicontrol.applaunch import _AppLaunch


__all__ = ['_Youtube', '_WebBrowsing', '_AppLaunch']

class UseCaseFactory:
    def __init__(self, device):
        self._device = device

    def create_use_case(self, uc_type: UseCaseType, **kwargs) -> UseCase:
        """
        Factory method to create a new use-case

        :rtype: UseCase
        """
        target_class = uc_type.value
        log.debug(f"Creating use case of type {target_class}")
        return globals()[target_class](self._device, **kwargs)
