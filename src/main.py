from __future__ import annotations

from core.agent import Agent
from config.settings import Settings


def main() -> None:
    settings = Settings.load()
    agent = Agent(settings=settings)
    agent.run()


if __name__ == "__main__":
    main()
