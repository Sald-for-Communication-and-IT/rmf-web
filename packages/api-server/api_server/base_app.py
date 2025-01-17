from abc import ABC, abstractmethod
from logging import Logger
from typing import Callable

from .authenticator import JwtAuthenticator
from .gateway import RmfGateway
from .models import User
from .repositories import RmfRepository, StaticFilesRepository
from .rmf_io import RmfBookKeeper, RmfEvents


class BaseApp(ABC):
    def __init__(self):
        self.authenticator: JwtAuthenticator
        self.auth_dep: Callable[..., User]
        self.rmf_repo: Callable[..., RmfRepository]
        self.logger: Logger
        self.static_files_repo: StaticFilesRepository

    @abstractmethod
    def rmf_events(self) -> RmfEvents:
        pass

    @abstractmethod
    def rmf_gateway(self) -> RmfGateway:
        pass

    @abstractmethod
    def rmf_bookkeeper(self) -> RmfBookKeeper:
        pass
