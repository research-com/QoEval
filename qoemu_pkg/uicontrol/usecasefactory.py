import logging as log

from qoemu_pkg.uicontrol.usecase import UseCaseType, UseCase
from youtube import _Youtube


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
