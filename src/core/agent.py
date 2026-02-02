from __future__ import annotations

from dataclasses import dataclass

from core.loop import run_loop
from config.settings import Settings


@dataclass
class Agent:
    settings: Settings

    def run(self) -> None:
        run_loop(self.settings)
