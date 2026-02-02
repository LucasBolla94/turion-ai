from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InboundMessage:
    channel: str
    sender: str
    text: str


class Channel(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send(self, recipient: str, text: str) -> None:
        raise NotImplementedError
