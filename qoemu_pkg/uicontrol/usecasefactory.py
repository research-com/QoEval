import logging as log

from usecase import UseCaseType, UseCase
from youtube import _Youtube
from webbrowsing import _WebBrowsing
from applaunch import _AppLaunch


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
